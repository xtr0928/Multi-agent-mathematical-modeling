# UI Bug Patterns — Common React Frontend Pitfalls

## Silent Catch Anti-Pattern

```jsx
// BAD — error swallowed, user sees nothing
const fetchData = async () => {
  try { const res = await client.get('/api/data'); return res.data; }
  catch { return []; }
};

// GOOD — error surfaced, user can retry
const [error, setError] = useState('');
const fetchData = async () => {
  setError('');
  try {
    const res = await client.get('/api/data');
    return res.data;
  } catch (err) {
    console.error('fetch failed:', err);
    setError(err.response?.status === 401
      ? '登录已过期，请重新登录'
      : '加载失败，请刷新页面');
    return [];
  }
};
```

## FullCalendar events: callback pattern (reliable) > Promise mode

**Both patterns work in FC v6**, but callback mode is more explicit and debuggable. Promise mode can fail silently when the backend is unreachable (resolves to empty array without error surface). If tasks don't appear, check backend health FIRST.

```jsx
// ⭐ RECOMMENDED — explicit callbacks, clear data flow
const fetchTasks = async (start, end) => {
  const res = await client.get(`/tasks?start=${start}&end=${end}`);
  return res.data.map(t => ({ id: t.id, title: t.title, start: t.startTime, end: t.endTime }));
};

<FullCalendar
  events={(info, successCallback, failureCallback) => {
    fetchTasks(info.startStr, info.endStr)
      .then(successCallback)
      .catch(err => { console.error(err); failureCallback(err); });
  }}
/>

// Also works (Promise mode) — but if backend is down, resolves silently to []
<FullCalendar events={(info) => fetchTasks(info.startStr, info.endStr)} />
```

**Root cause checklist when tasks are invisible:**
1. Is backend running? `curl localhost:3000/api/health`
2. Does API return tasks? `curl .../api/tasks -H "Authorization: Bearer $TOKEN"`
3. Browser loading stale frontend? Restart Vite + hard-refresh
4. Token stored in localStorage? Check key name matches AuthContext

## useEffect Auth Race

100ms delay needed because FullCalendar may not have mounted when the effect fires.

```jsx
useEffect(() => {
  if (!user) { setFetchError(''); return; }
  const t = setTimeout(() => {
    calendarRef.current?.getApi()?.refetchEvents();
  }, 100);
  return () => clearTimeout(t);
}, [user]);
```

## AbortController + FullCalendar: NEVER USE

**Triggered highest-frustration user response ("你写的什么玩意") in 2026-07-02 session.**

GLM recommended AbortController for race-condition protection. Implementation caused **all tasks to disappear — both old and new**.

```jsx
// ❌ BROKEN: abortRef.current.abort() kills prev request.
// Cancelled request returns [] without calling failureCallback.
// FullCalendar never learns it ended → stuck in loading forever.
// All future refetchEvents() silently ignored.
if (err.name === 'CanceledError') return [];  // DOES NOT CALL fail()!
```

**Why**: `useEffect([user])` + `refetchEvents()` triggers a second fetch immediately after mount. Second aborts first → aborted fetch doesn't call `failureCallback` → FC stuck.

**Fix**: Remove AbortController. FullCalendar handles stale requests internally. Always call either `successCallback` or `failureCallback`.

**Rule**: AbortController is NEVER a "nice-to-have". Only add it when BOTH callbacks are guaranteed on every code path. For FullCalendar, skip it.
