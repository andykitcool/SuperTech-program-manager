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
