import { createLogger } from 'redux-logger'
import { combineReducers, configureStore, Tuple } from '@reduxjs/toolkit'
import { menuReducers } from './reducers/menu'
import { taskReducers } from './reducers/task'
import { TypedUseSelectorHook, useSelector } from 'react-redux'

const loggerMiddleware = createLogger({
  collapsed: true,
  duration: true,
})

export const rootReducer = combineReducers({
  menu: menuReducers,
  task: taskReducers,
})

export const store = configureStore({
  reducer: rootReducer,
  devTools: import.meta.env.DEV,
  middleware: () =>
    import.meta.env.DEV ? new Tuple<any>(loggerMiddleware) : new Tuple(),
})

export type RootState = ReturnType<typeof store.getState>

export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector
