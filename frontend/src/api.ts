const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const getHeaders = () => {
  const token = localStorage.getItem('token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };
};

export const fetcher = (url: string) => fetch(`${API_URL}${url}`, { headers: getHeaders() }).then(res => res.json());

export const login = async (username: string, password: string) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  
  const res = await fetch(`${API_URL}/auth/token`, {
    method: 'POST',
    body: params,
  });
  if (!res.ok) throw new Error("Login failed");
  return res.json();
};
