import { ApiError, apiRequest } from './http'

export type LoginCredentials = {
  login: string
  password: string
}

export type RegistrationData = {
  email: string
  username: string
  first_name: string
  last_name: string
  password: string
}

export type TokenResponse = {
  access_token: string
  token_type: 'bearer'
}

export type User = {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  created_at: string
}

export type AuthenticatedSession = {
  accessToken: string
  user: User
}

let pendingSessionRestore: Promise<AuthenticatedSession> | null = null
let pendingTokenRefresh: Promise<TokenResponse> | null = null

export function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

export function register(data: RegistrationData): Promise<User> {
  return apiRequest<User>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function refreshAccessToken(): Promise<TokenResponse> {
  if (!pendingTokenRefresh) {
    pendingTokenRefresh = apiRequest<TokenResponse>('/auth/refresh', {
      method: 'POST',
    }).finally(() => {
      pendingTokenRefresh = null
    })
  }

  return pendingTokenRefresh
}

export function getCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>('/auth/me', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })
}

export function restoreCurrentSession(): Promise<AuthenticatedSession> {
  if (!pendingSessionRestore) {
    pendingSessionRestore = (async () => {
      try {
        const token = await refreshAccessToken()
        const user = await getCurrentUser(token.access_token)

        return {
          accessToken: token.access_token,
          user,
        }
      } finally {
        pendingSessionRestore = null
      }
    })()
  }

  return pendingSessionRestore
}

export async function apiRequestWithAuth<T>(
  path: string,
  accessToken: string,
  options: RequestInit = {},
): Promise<{ accessToken: string; data: T }> {
  const request = (token: string) =>
    apiRequest<T>(path, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
      },
    })

  try {
    return {
      accessToken,
      data: await request(accessToken),
    }
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) {
      throw error
    }

    const refreshedToken = await refreshAccessToken()

    return {
      accessToken: refreshedToken.access_token,
      data: await request(refreshedToken.access_token),
    }
  }
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout', {
    method: 'POST',
  })
}
