import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';
import { toSignal } from '@angular/core/rxjs-interop';
import { ApiService } from './api.service';
import { AccessTokenResponse, TokenPair, User } from './models';

const ACCESS_KEY = 'dp_access_token';
const REFRESH_KEY = 'dp_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  private readonly userSubject = new BehaviorSubject<User | null>(null);
  readonly currentUser$ = this.userSubject.asObservable();
  readonly currentUser = toSignal(this.currentUser$, { initialValue: null });

  get accessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
  }

  get refreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  }

  get isAuthenticated(): boolean {
    return this.accessToken !== null;
  }

  login(email: string, password: string): Observable<User> {
    return this.api.login(email, password).pipe(
      tap((tokens) => this.setTokens(tokens)),
      switchMap(() => this.loadCurrentUser()),
    );
  }

  register(email: string, password: string): Observable<User> {
    return this.api.register(email, password).pipe(
      tap((tokens) => this.setTokens(tokens)),
      switchMap(() => this.loadCurrentUser()),
    );
  }

  logout(): void {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this.userSubject.next(null);
    this.router.navigate(['/login']);
  }

  refreshAccessToken(): Observable<AccessTokenResponse> {
    const rt = this.refreshToken;
    if (!rt) return throwError(() => new Error('No refresh token'));
    return this.api.refreshToken(rt).pipe(
      tap((res) => localStorage.setItem(ACCESS_KEY, res.access_token)),
    );
  }

  setTokens(pair: TokenPair): void {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  }

  loadCurrentUser(): Observable<User> {
    return this.api.me().pipe(tap((user) => this.userSubject.next(user)));
  }
}
