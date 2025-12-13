import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';

const ACCESS_KEY = 'dp_access_token';
const REFRESH_KEY = 'dp_refresh_token';
const BASE = 'http://localhost:8000';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpTesting: HttpTestingController;
  let authService: AuthService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpTesting = TestBed.inject(HttpTestingController);
    authService = TestBed.inject(AuthService);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  it('adds Authorization Bearer header when access token exists', () => {
    localStorage.setItem(ACCESS_KEY, 'mytoken');
    http.get(`${BASE}/api/documents/`).subscribe();

    const req = httpTesting.expectOne(`${BASE}/api/documents/`);
    expect(req.request.headers.get('Authorization')).toBe('Bearer mytoken');
    req.flush([]);
  });

  it('does not add Authorization header when no token', () => {
    http.get(`${BASE}/api/documents/`).subscribe();

    const req = httpTesting.expectOne(`${BASE}/api/documents/`);
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });

  it('on 401 from non-auth endpoint: refreshes token and retries', () => {
    localStorage.setItem(ACCESS_KEY, 'old');
    localStorage.setItem(REFRESH_KEY, 'rt');
    let response: unknown;
    http.get(`${BASE}/api/documents/`).subscribe((r) => (response = r));

    // First attempt → 401
    httpTesting.expectOne(`${BASE}/api/documents/`).flush(
      { detail: 'unauthorized' },
      { status: 401, statusText: 'Unauthorized' },
    );

    // Refresh call
    const refreshReq = httpTesting.expectOne((r) => r.url.includes('/auth/refresh'));
    refreshReq.flush({ access_token: 'new_acc', token_type: 'bearer' });

    // Retry original request with new token
    const retryReq = httpTesting.expectOne(`${BASE}/api/documents/`);
    expect(retryReq.request.headers.get('Authorization')).toBe('Bearer new_acc');
    retryReq.flush({ items: [] });

    expect(response).toEqual({ items: [] });
  });

  it('on 401 from auth endpoint: calls logout without retry', () => {
    const logoutSpy = vi.spyOn(authService, 'logout').mockImplementation(() => undefined);
    http.post(`${BASE}/auth/login`, {}).subscribe({ error: () => undefined });

    httpTesting.expectOne(`${BASE}/auth/login`).flush(
      {},
      { status: 401, statusText: 'Unauthorized' },
    );

    expect(logoutSpy).toHaveBeenCalled();
  });

  it('on 401 from non-auth endpoint with failed refresh: calls logout', () => {
    localStorage.setItem(ACCESS_KEY, 'old');
    localStorage.setItem(REFRESH_KEY, 'rt');
    const logoutSpy = vi.spyOn(authService, 'logout').mockImplementation(() => undefined);
    http.get(`${BASE}/api/documents/`).subscribe({ error: () => undefined });

    httpTesting.expectOne(`${BASE}/api/documents/`).flush(
      {},
      { status: 401, statusText: 'Unauthorized' },
    );

    httpTesting
      .expectOne((r) => r.url.includes('/auth/refresh'))
      .flush({}, { status: 401, statusText: 'Unauthorized' });

    expect(logoutSpy).toHaveBeenCalled();
  });
});
