export interface TaskType {
  id: number
  description: string
  last_modified: string
  name: string
  owner: string
  owner__username: string
  shared: boolean
}

export type TaskDetailType = {
  id: number
  description: string
  name: string
  shared: boolean
  code: string
}
