import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'https://ferrik-bot-zvev.onrender.com/api/v1';

export const api = {
  getMenu: (params) => axios.get(`${API_BASE}/menu`, { params }),
  getMoodMenu: (tag) => axios.get(`${API_BASE}/menu/mood/${tag}`),
  getRestaurants: () => axios.get(`${API_BASE}/restaurants`),
  createOrder: (data) => axios.post(`${API_BASE}/order`, data),
  validatePromo: (code) => axios.post(`${API_BASE}/promo/validate`, { code }),
  getUserOrders: (userId) => axios.get(`${API_BASE}/orders/user/${userId}`)
};
