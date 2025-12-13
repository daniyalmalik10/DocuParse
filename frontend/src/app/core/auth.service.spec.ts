import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';
import { vi } from 'vitest';
import { AuthService } from './auth.service';

const ACCESS_KEY = 'dp_access_token';
const REFRESH_KEY = 'dp_refresh_token';
const BASE = 'http://localhost:8000';

describe('AuthService', () => {
  let service: AuthService;
  let httpTesting: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    service = TestBed.inject(AuthService);
    httpTesting = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpTesting.verify();
    localStorage.clear();
  });

  describe('accessToken getter', () => {
    it('returns null when localStorage is empty', () => {
      expect(service.accessToken).toBeNull();
    });

    it('returns stored value when token is present', () => {
      localStorage.setItem(ACCESS_KEY, 'tok123');
      expect(service.accessToken).toBe('tok123');
    });
  });

  describe('isAuthenticated getter', () => {
    it('returns false when no access token', () => {
      expect(service.isAuthenticated).toBe(false);
    });

    it('returns true when access token exists', () => {
      localStorage.setItem(ACCESS_KEY, 'tok');
      expect(service.isAuthenticated).toBe(true);
    });
  });

  describe('setTokens()', () => {
    it('writes both tokens to localStorage', () => {
      service.setTokens({ access_token: 'acc', refresh_token: 'ref', token_type: 'bearer' });
      expect(localStorage.getItem(ACCESS_KEY)).toBe('acc');
      expect(localStorage.getItem(REFRESH_KEY)).toBe('ref');
    });
  });

  describe('login()', () => {
    it('POSTs /auth/login, stores tokens, then GETs /auth/me, emits user', () => {
      let result: { email: string } | undefined;
      service.login('a@b.com', 'pass').subscribe((u) => (result = u));

      const loginReq = httpTesting.expectOne(`${BASE}/auth/login`);
      expect(loginReq.request.method).toBe('POST');
      loginReq.flush({ access_token: 'a', refresh_token: 'r', token_type: 'bearer' });

      const meReq = httpTesting.expectOne(`${BASE}/auth/me`);
      expect(meReq.request.method).toBe('GET');
      meReq.flush({ id: '1', email: 'a@b.com' });

      expect(localStorage.getItem(ACCESS_KEY)).toBe('a');
      expect(result?.email).toBe('a@b.com');
    });
  });

  describe('logout()', () => {
    it('clears localStorage and navigates to /login', () => {
      localStorage.setItem(ACCESS_KEY, 'x');
      localStorage.setItem(REFRESH_KEY, 'y');
      const router = TestBed.inject(Router);
      const spy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

      service.logout();

      expect(localStorage.getItem(ACCESS_KEY)).toBeNull();
      expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
      expect(spy).toHaveBeenCalledWith(['/login']);
    });
  });

  describe('refreshAccessToken()', () => {
    it('returns error observable when no refresh token', () => {
      let err: Error | undefined;
      service.refreshAccessToken().subscribe({ error: (e: Error) => (err = e) });
      expect(err?.message).toBe('No refresh token');
    });

    it('POSTs /auth/refresh and stores new access token', () => {
      localStorage.setItem(REFRESH_KEY, 'rt');
      service.refreshAccessToken().subscribe();

      const req = httpTesting.expectOne(`${BASE}/auth/refresh`);
      expect(req.request.method).toBe('POST');
      req.flush({ access_token: 'new_acc', token_type: 'bearer' });

      expect(localStorage.getItem(ACCESS_KEY)).toBe('new_acc');
    });
  });
});
