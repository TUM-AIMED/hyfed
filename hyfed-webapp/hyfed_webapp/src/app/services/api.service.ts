/**
    Copyright 2021 Julian Matschinske. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

const ACCESS_EXPIRES = 20 * 60 * 1000; // 20 minutes
const REFRESH_EXPIRES = 24 * 60 * 60 * 1000; // 1 day

@Injectable({
  providedIn: 'root',
})
export class ApiService {

  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private accessExpires: number | null = null;
  private refreshExpires: number | null = null;

  constructor(private http: HttpClient) {
    this.accessToken = localStorage.getItem('accessToken');
    this.refreshToken = localStorage.getItem('refreshToken');
    this.accessExpires = Number(localStorage.getItem('accessExpires'));
    this.refreshExpires = Number(localStorage.getItem('refreshExpires'));

    if (this.accessToken) {
      document.cookie = `access_token=${this.accessToken};path=/;domain=${environment.cookieDomain};`;
    }
  }

  public setAccessToken(token: string | null) {
    this.accessToken = token;
    if (token === null) {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('accessExpires');

      document.cookie = `access_token=;path=/;domain=${environment.cookieDomain};`;
    } else {
      this.accessExpires = new Date().getTime() + ACCESS_EXPIRES;
      localStorage.setItem('accessToken', this.accessToken);
      localStorage.setItem('accessExpires', `${this.accessExpires}`);

      document.cookie = `access_token=${this.accessToken};path=/;domain=${environment.cookieDomain};`;
    }
  }

  public getAccessExpires(): number | null {
    return this.accessExpires;
  }

  public setRefreshToken(token: string | null) {
    this.refreshToken = token;
    if (token === null) {
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('refreshExpires');
    } else {
      this.refreshExpires = new Date().getTime() + REFRESH_EXPIRES;
      localStorage.setItem('refreshToken', this.refreshToken);
      localStorage.setItem('refreshExpires', `${this.refreshExpires}`);
    }
  }

  public async refreshAccess(): Promise<boolean> {
    if (!this.refreshToken) {
      return false;
    }
    return await (this.http.post(`${environment.apiUrl}/auth/token/refresh/`, {
      refresh: this.refreshToken,
    }).toPromise()).then(async (json: any) => {
      this.setAccessToken(json.access);
      return true;
    }).catch(async (reason) => {
      if (reason.status === 401) {
        console.warn(`refresh token invalid`);
        this.setRefreshToken(null);
      }
      return false;
    });
  }

  private async checkAuth(): Promise<boolean> {
    if (!this.accessToken) {
      return false;
    }
    if (this.accessExpires <= new Date().getTime()) {
      console.warn('access token expired');
      return await this.refreshAccess();
    }
    return true;
  }

  public async get<T>(url: string, auth = true): Promise<T> {
    if (auth) {
      if (!await this.checkAuth()) {
        return null;
      }
    } else {
      url = this.appendNoAuth(url);
    }
    return this.http.get(`${environment.apiUrl}${url}`, {headers: this.getHeaders(auth)}).toPromise() as Promise<T>;
  }

  public async post<T>(url: string, body: any, auth = true): Promise<T> {
    if (auth) {
      await this.checkAuth();
    } else {
      url = this.appendNoAuth(url);
    }
    return this.http.post(`${environment.apiUrl}${url}`, body, {headers: this.getHeaders(auth)}).toPromise() as Promise<T>;
  }

  public async put<T>(url: string, body: any, auth = true): Promise<T> {
    if (auth) {
      await this.checkAuth();
    } else {
      url = this.appendNoAuth(url);
    }
    return this.http.put(`${environment.apiUrl}${url}`, body, {headers: this.getHeaders(auth)}).toPromise() as Promise<T>;
  }

  public async delete<T>(url: string, auth = true): Promise<T> {
    if (auth) {
      await this.checkAuth();
    } else {
      url = this.appendNoAuth(url);
    }
    return this.http.delete(`${environment.apiUrl}${url}`, {headers: this.getHeaders(auth)}).toPromise() as Promise<T>;
  }

  public getHeaders(auth: boolean): { [p: string]: string } {
    if (!auth || !this.accessToken) {
      return {};
    }
    return {Authorization: `Bearer ${this.accessToken}`};
  }

  public hasTokens(): boolean {
    return !!this.accessToken || !!this.refreshToken;
  }

  public getAccessToken(): string | null {
    return this.accessToken;
  }

  public getRefreshToken(): string | null {
    return this.refreshToken;
  }

  private appendNoAuth(url: string): string {
    if (url.indexOf('?') === -1) {
      return `${url}?noauth=1`;
    } else {
      return `${url}&noauth=1`;
    }
  }

}
