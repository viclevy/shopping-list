import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('./views/LoginView.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'shopping-list',
    component: () => import('./views/ShoppingListView.vue'),
    meta: { auth: true },
  },
  {
    path: '/product/:id',
    name: 'product-detail',
    component: () => import('./views/ProductDetailView.vue'),
    meta: { auth: true },
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('./views/HistoryView.vue'),
    meta: { auth: true },
  },
  {
    path: '/analytics',
    name: 'analytics',
    component: () => import('./views/AnalyticsView.vue'),
    meta: { auth: true },
  },
  {
    path: '/admin/users',
    name: 'admin-users',
    component: () => import('./views/AdminUsersView.vue'),
    meta: { auth: true, admin: true },
  },
  {
    path: '/stores',
    name: 'stores',
    component: () => import('./views/StoresView.vue'),
    meta: { auth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.auth && !token) {
    next('/login')
  } else if (to.meta.guest && token) {
    next('/')
  } else {
    next()
  }
})

export default router
