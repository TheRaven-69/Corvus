import { apiRequest } from './http'

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

let pendingSessionRestore: Promise<User> | null = null

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
  return apiRequest<TokenResponse>('/auth/refresh', {
    method: 'POST',
  })
}

export function getCurrentUser(accessToken: string): Promise<User> {
  return apiRequest<User>('/auth/me', {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  })
}

export function restoreCurrentUser(): Promise<User> {
  if (!pendingSessionRestore) {
    pendingSessionRestore = (async () => {
      try {
        const token = await refreshAccessToken()
        return await getCurrentUser(token.access_token)
      } finally {
        pendingSessionRestore = null
      }
    })()
  }

  return pendingSessionRestore
}

export function logout(): Promise<void> {
  return apiRequest<void>('/auth/logout', {
    method: 'POST',
  })
}
