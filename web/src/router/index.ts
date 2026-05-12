import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    // Admin routes
    {
      path: '/admin/login',
      name: 'AdminLogin',
      component: () => import('@/views/admin/Login.vue'),
      meta: { layout: 'blank' },
    },
    {
      path: '/admin',
      component: () => import('@/views/admin/Dashboard.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'AdminDashboard',
          component: () => import('@/views/admin/ActivityList.vue'),
        },
        {
          path: 'activity/create',
          name: 'ActivityCreate',
          component: () => import('@/views/admin/ActivityForm.vue'),
        },
        {
          path: 'activity/:id/edit',
          name: 'ActivityEdit',
          component: () => import('@/views/admin/ActivityForm.vue'),
        },
        {
          path: 'activity/:id/programs',
          name: 'ProgramList',
          component: () => import('@/views/admin/ProgramList.vue'),
        },
        {
          path: 'settings',
          name: 'Settings',
          component: () => import('@/views/admin/Settings.vue'),
        },
        {
          path: 'users',
          name: 'UserManagement',
          component: () => import('@/views/admin/UserManagement.vue'),
        },
        {
          path: 'change-password',
          name: 'ChangePassword',
          component: () => import('@/views/admin/ChangePassword.vue'),
        },
        {
          path: 'wotu-sync',
          name: 'WotuSync',
          component: () => import('@/views/admin/WotuSync.vue'),
        },
        {
          path: 'photo-manager',
          name: 'PhotoManager',
          component: () => import('@/views/admin/PhotoManager.vue'),
        },
        {
          path: 'photo-manager/activity/:id',
          name: 'PhotoGallery',
          component: () => import('@/views/admin/PhotoGallery.vue'),
        },
        {
          path: 'music-library',
          name: 'MusicLibrary',
          component: () => import('@/views/admin/MusicLibrary.vue'),
        },
        {
          path: 'decoration-manager',
          name: 'DecorationManager',
          component: () => import('@/views/admin/DecorationManager.vue'),
        },
        {
          path: 'print-settings',
          name: 'PrintSettings',
          component: () => import('@/views/admin/PrintSettings.vue'),
        },
        {
          path: 'print-orders',
          name: 'PrintOrders',
          component: () => import('@/views/admin/PrintOrders.vue'),
        },
      ],
    },

    // Public routes - 家长只能通过COZE智能体返回的链接访问节目详情页
    {
      path: '/',
      name: 'NotFound',
      component: () => import('@/views/public/NotFound.vue'),
    },
    {
      path: '/a/:pathMatch(.*)*',
      name: 'NotFoundActivity',
      component: () => import('@/views/public/NotFound.vue'),
    },
    {
      path: '/lobby/:activityId',
      name: 'LobbyPlayer',
      component: () => import('@/views/lobby/LobbyPlayer.vue'),
    },
    {
      path: '/m/activity-admin',
      name: 'MobileActivityAdmin',
      component: () => import('@/views/mobile/MobileActivityAdmin.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/m/print-admin',
      name: 'MobilePrintAdmin',
      component: () => import('@/views/mobile/MobilePrintAdmin.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/p/index',
      name: 'PublicActivityIndex',
      component: () => import('@/views/public/ActivityIndex.vue'),
    },
    {
      path: '/p/:activityId(\\d+)',
      name: 'PublicActivityDetail',
      component: () => import('@/views/public/ActivityDetail.vue'),
    },
    {
      path: '/p/:token',
      name: 'PublicProgram',
      component: () => import('@/views/public/ProgramDetail.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'CatchAll',
      component: () => import('@/views/public/NotFound.vue'),
    },
  ],
})

router.beforeEach((to, _from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      next({ name: 'AdminLogin' })
      return
    }
  }
  next()
})

export default router
