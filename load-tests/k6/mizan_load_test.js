import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

const BASE_URL = (__ENV.BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');
const RUN_ID = __ENV.RUN_ID || `${Date.now()}`;
const PASSWORD = __ENV.PASSWORD || 'LoadPass123!';
const USERS = Number(__ENV.USERS || 50);
const MODE = __ENV.MODE || 'smoke';

const authFailures = new Rate('auth_failures');
const dashboardLatency = new Trend('dashboard_latency');
const createActLatency = new Trend('create_act_latency');
const notificationLatency = new Trend('notification_latency');

const profiles = {
  smoke: { vus: 2, duration: '30s' },
  normal: {
    stages: [
      { duration: '2m', target: 25 },
      { duration: '5m', target: 100 },
      { duration: '2m', target: 0 },
    ],
  },
  spike: {
    stages: [
      { duration: '30s', target: 50 },
      { duration: '30s', target: 500 },
      { duration: '2m', target: 500 },
      { duration: '30s', target: 0 },
    ],
  },
  stress: {
    stages: [
      { duration: '2m', target: 100 },
      { duration: '3m', target: 250 },
      { duration: '3m', target: 500 },
      { duration: '3m', target: 1000 },
      { duration: '2m', target: 0 },
    ],
  },
  soak: {
    stages: [
      { duration: '5m', target: 100 },
      { duration: '30m', target: 100 },
      { duration: '5m', target: 0 },
    ],
  },
};

export const options = {
  scenarios: {
    app_flow: {
      executor: profiles[MODE].stages ? 'ramping-vus' : 'constant-vus',
      ...(profiles[MODE].stages ? { stages: profiles[MODE].stages } : profiles[MODE]),
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<800', 'p(99)<2000'],
    dashboard_latency: ['p(95)<700'],
    create_act_latency: ['p(95)<1000'],
    notification_latency: ['p(95)<500'],
    auth_failures: ['rate<0.01'],
  },
};

function jsonHeaders(token) {
  return {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    timeout: '10s',
  };
}

function userFor(index) {
  return {
    username: `load_${RUN_ID}_${index}`,
    email: `load_${RUN_ID}_${index}@example.test`,
    password: PASSWORD,
  };
}

export function setup() {
  const users = [];
  for (let i = 0; i < USERS; i += 1) {
    const user = userFor(i);
    const res = http.post(`${BASE_URL}/auth/register`, JSON.stringify(user), jsonHeaders());
    check(res, { 'register ok or duplicate': (r) => r.status === 200 || r.status === 409 });
    users.push(user);
  }
  return { users };
}

function login(user) {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    jsonHeaders(),
  );
  const ok = check(res, { 'login ok': (r) => r.status === 200 });
  authFailures.add(!ok);
  if (!ok) return null;
  return res.json('access_token');
}

export default function (data) {
  const user = data.users[(__VU + __ITER) % data.users.length];
  const token = login(user);
  if (!token) {
    sleep(1);
    return;
  }

  group('dashboard/home', () => {
    let res = http.get(`${BASE_URL}/dashboard/stats`, jsonHeaders(token));
    dashboardLatency.add(res.timings.duration);
    check(res, { 'dashboard stats 200': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/dashboard/category-analytics`, jsonHeaders(token));
    check(res, { 'category analytics 200': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/sadaqah/daily`, jsonHeaders(token));
    check(res, { 'daily acts 200': (r) => r.status === 200 });
  });

  group('create activity', () => {
    const requestId = `${RUN_ID}-${__VU}-${__ITER}`;
    const res = http.post(
      `${BASE_URL}/sadaqah/jar/add-star?type=Kindness&request_id=${requestId}`,
      null,
      jsonHeaders(token),
    );
    createActLatency.add(res.timings.duration);
    check(res, { 'add star 200': (r) => r.status === 200 });
  });

  group('notifications/books/search-like reads', () => {
    let res = http.get(`${BASE_URL}/notifications/unread-count`, jsonHeaders(token));
    notificationLatency.add(res.timings.duration);
    check(res, { 'unread count 200': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/notifications/?limit=20&offset=0`, jsonHeaders(token));
    check(res, { 'notifications list 200': (r) => r.status === 200 });

    res = http.get(`${BASE_URL}/books/?limit=20&offset=0`, jsonHeaders(token));
    check(res, { 'books list 200': (r) => r.status === 200 });
  });

  sleep(Math.random() * 2 + 1);
}
