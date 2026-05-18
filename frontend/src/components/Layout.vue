<template>
  <div class="layout-wrapper">
    <!-- Sidebar -->
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-logo">
        <el-icon size="24" color="#409EFF"><cpu /></el-icon>
        <span v-show="!sidebarCollapsed" class="logo-text">模型训练平台</span>
      </div>

      <el-menu
        :default-active="activeMenuPath"
        :collapse="sidebarCollapsed"
        background-color="#001529"
        text-color="#a6adb4"
        active-text-color="#409EFF"
        :collapse-transition="false"
        class="sidebar-menu"
        router
      >
        <el-menu-item index="/projects">
          <el-icon><grid /></el-icon>
          <template #title>项目概览</template>
        </el-menu-item>

        <template v-if="currentProjectId">
          <el-sub-menu index="project-submenu">
            <template #title>
              <el-icon><folder-opened /></el-icon>
              <span>{{ currentProjectName }}</span>
            </template>
            <el-menu-item :index="`/projects/${currentProjectId}/datasets`">
              <el-icon><files /></el-icon>
              <template #title>数据集管理</template>
            </el-menu-item>
            <el-menu-item :index="`/projects/${currentProjectId}/canvas`">
              <el-icon><connection /></el-icon>
              <template #title>画布编辑</template>
            </el-menu-item>
            <el-menu-item :index="`/projects/${currentProjectId}/jobs`">
              <el-icon><data-line /></el-icon>
              <template #title>训练任务</template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>

      <div class="sidebar-collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
        <el-icon>
          <component :is="sidebarCollapsed ? 'DArrowRight' : 'DArrowLeft'" />
        </el-icon>
      </div>
    </div>

    <!-- Main content area -->
    <div class="main-area">
      <!-- Top header -->
      <div class="top-header">
        <div class="header-breadcrumb">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/projects' }">项目概览</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentProjectId && currentProjectName">
              {{ currentProjectName }}
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentPageTitle">{{ currentPageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-title">可视化小模型训练平台</div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleUserCommand">
            <div class="user-info">
              <el-avatar size="32" :style="{ background: '#409EFF', fontSize: '14px' }">
                {{ userInitial }}
              </el-avatar>
              <span class="username">{{ username }}</span>
              <el-icon class="el-icon--right"><arrow-down /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <el-icon><user /></el-icon>
                  {{ username }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><switch-button /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>

      <!-- Page content -->
      <div class="page-content" :class="{ 'full-width': fullWidth }">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

const props = defineProps({
  fullWidth: {
    type: Boolean,
    default: false
  }
})

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const projectStore = useProjectStore()

const sidebarCollapsed = ref(false)

const currentProjectId = computed(() => route.params.id || null)

const currentProjectName = computed(() => {
  if (!currentProjectId.value) return ''
  return projectStore.currentProject?.name || `项目 ${currentProjectId.value}`
})

const activeMenuPath = computed(() => route.path)

const currentPageTitle = computed(() => {
  const routeMap = {
    Datasets: '数据集管理',
    Canvas: '画布编辑',
    TrainingJobs: '训练任务',
    JobDetail: '任务详情'
  }
  return routeMap[route.name] || ''
})

const username = computed(() => authStore.user?.username || authStore.user?.name || '用户')
const userInitial = computed(() => (username.value || 'U')[0].toUpperCase())

async function handleUserCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确认退出登录吗？', '退出确认', {
      type: 'warning',
      confirmButtonText: '退出',
      cancelButtonText: '取消'
    })
    authStore.logout()
  }
}
</script>

<style scoped>
.layout-wrapper {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 220px;
  background: #001529;
  display: flex;
  flex-direction: column;
  transition: width 0.25s ease;
  flex-shrink: 0;
  overflow: hidden;
  z-index: 100;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  height: 60px;
  overflow: hidden;
  white-space: nowrap;
}

.logo-text {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.sidebar-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}

:deep(.sidebar-menu .el-menu-item.is-active) {
  background-color: rgba(64, 158, 255, 0.15) !important;
  border-right: 3px solid #409EFF;
}

:deep(.sidebar-menu .el-menu-item:hover),
:deep(.sidebar-menu .el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

:deep(.sidebar-menu .el-sub-menu .el-menu-item) {
  background-color: rgba(0, 0, 0, 0.2) !important;
}

:deep(.sidebar-menu .el-sub-menu .el-menu-item.is-active) {
  background-color: rgba(64, 158, 255, 0.2) !important;
}

.sidebar-collapse-btn {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a6adb4;
  cursor: pointer;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  transition: color 0.2s, background 0.2s;
}

.sidebar-collapse-btn:hover {
  color: #409EFF;
  background: rgba(255, 255, 255, 0.05);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f7fa;
}

.top-header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  padding: 0 24px;
  flex-shrink: 0;
  gap: 16px;
  z-index: 50;
}

.header-breadcrumb {
  flex: 1;
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a2e;
  white-space: nowrap;
}

.header-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: background 0.2s;
}

.user-info:hover {
  background: #f5f7fa;
}

.username {
  font-size: 14px;
  color: #303133;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-content {
  flex: 1;
  overflow: auto;
}

.page-content.full-width {
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
