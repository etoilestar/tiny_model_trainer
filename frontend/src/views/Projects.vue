<template>
  <Layout>
    <div class="projects-page">
      <div class="page-header">
        <div>
          <h2>我的项目</h2>
          <p class="subtitle">管理您的模型训练项目</p>
        </div>
        <el-button type="primary" :icon="Plus" size="large" @click="openCreateDialog">
          新建项目
        </el-button>
      </div>

      <div v-if="projectStore.loading" class="loading-container">
        <el-skeleton :rows="3" animated />
      </div>

      <div v-else-if="projectStore.projects.length === 0" class="empty-state">
        <el-empty description="暂无项目，点击新建项目开始">
          <el-button type="primary" @click="openCreateDialog">新建项目</el-button>
        </el-empty>
      </div>

      <div v-else class="projects-grid">
        <el-card
          v-for="project in projectStore.projects"
          :key="project.id"
          class="project-card"
          shadow="hover"
        >
          <div class="project-card-header">
            <el-icon size="24" color="#409EFF"><folder /></el-icon>
            <el-tag size="small" type="success">活跃</el-tag>
          </div>
          <h3 class="project-name">{{ project.name }}</h3>
          <p class="project-desc">{{ project.description || '暂无描述' }}</p>
          <div class="project-meta">
            <el-icon><calendar /></el-icon>
            <span>{{ formatDate(project.created_at) }}</span>
          </div>
          <div class="project-actions">
            <el-button type="primary" size="small" @click="enterProject(project)">
              进入
            </el-button>
            <el-dropdown trigger="click" @command="(cmd) => handleProjectCommand(cmd, project)">
              <el-button size="small">
                更多
                <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="canvas">画布编辑</el-dropdown-item>
                  <el-dropdown-item command="datasets">数据集管理</el-dropdown-item>
                  <el-dropdown-item command="jobs">训练任务</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>
                    <span style="color: #f56c6c">删除项目</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 新建项目对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建项目"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-width="90px"
        size="large"
      >
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入项目名称" clearable />
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入项目描述（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="handleCreateProject">
          创建
        </el-button>
      </template>
    </el-dialog>
  </Layout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import Layout from '@/components/Layout.vue'
import { useProjectStore } from '@/stores/project'

const router = useRouter()
const projectStore = useProjectStore()
const createDialogVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref(null)

const createForm = reactive({ name: '', description: '' })
const createRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }]
}

function formatDate(dateStr) {
  return dateStr ? dayjs(dateStr).format('YYYY-MM-DD HH:mm') : '-'
}

function openCreateDialog() {
  createForm.name = ''
  createForm.description = ''
  createDialogVisible.value = true
}

function enterProject(project) {
  projectStore.setCurrentProject(project)
  router.push(`/projects/${project.id}/canvas`)
}

function handleProjectCommand(cmd, project) {
  projectStore.setCurrentProject(project)
  if (cmd === 'canvas') router.push(`/projects/${project.id}/canvas`)
  else if (cmd === 'datasets') router.push(`/projects/${project.id}/datasets`)
  else if (cmd === 'jobs') router.push(`/projects/${project.id}/jobs`)
  else if (cmd === 'delete') confirmDelete(project)
}

async function confirmDelete(project) {
  await ElMessageBox.confirm(
    `确认要删除项目 "${project.name}" 吗？此操作不可恢复。`,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  )
  try {
    await projectStore.removeProject(project.id)
    ElMessage.success('项目已删除')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '删除失败')
  }
}

async function handleCreateProject() {
  if (!createFormRef.value) return
  const valid = await createFormRef.value.validate().catch(() => false)
  if (!valid) return
  createLoading.value = true
  try {
    await projectStore.addProject({ name: createForm.name, description: createForm.description })
    ElMessage.success('项目创建成功')
    createDialogVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || '创建失败')
  } finally {
    createLoading.value = false
  }
}

onMounted(() => projectStore.fetchProjects())
</script>

<style scoped>
.projects-page {
  padding: 24px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 4px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
}

.loading-container {
  padding: 24px 0;
}

.empty-state {
  padding: 80px 0;
  display: flex;
  justify-content: center;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.project-card {
  border-radius: 12px;
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.project-card:hover {
  transform: translateY(-2px);
}

.project-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.project-name {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 8px;
}

.project-desc {
  font-size: 14px;
  color: #909399;
  margin-bottom: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #c0c4cc;
  margin-bottom: 16px;
}

.project-actions {
  display: flex;
  gap: 8px;
}
</style>
