import React, { useState } from 'react'
import {
  useTheme,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from '@mui/material'
import { KeyOutlined, LogoutOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { toast } from 'react-toastify'

import {
  LocalStorageKey,
  removeFromLocalStorage,
} from 'utils/localStorageUtils'
import { activeItem, openDrawer } from 'store/reducers/menu'
import { MessageText } from 'utils/messages'
import { MethodHTTP, fetchApi } from 'services/api'
import { endpoints } from 'services/endpoints'
import { Palette } from 'themes/palette'

interface ProfileTabProps {
  setOpen: (open: boolean) => void
}

export const ProfileTab = ({ setOpen }: ProfileTabProps) => {
  const theme = useTheme()
  const dispatch = useDispatch()
  const navigate = useNavigate()

  const [selectedIndex, setSelectedIndex] = useState(-1)

  const handleListItemClick = (index: number, id: string) => {
    dispatch(openDrawer(true))
    dispatch(activeItem(id))
    setSelectedIndex(index)
    navigate(`/${id}`)
    setOpen(false)
  }

  const handleLogout = async () => {
    fetchApi({
      url: endpoints.auth.logout,
      method: MethodHTTP.POST,
    }).then(() => {
      setSelectedIndex(1)
      removeFromLocalStorage(LocalStorageKey.USER)
      toast.success(MessageText.logoutSuccess)
      navigate('/login')
    })
  }

  const themePalette = Palette('light')

  return (
    <List
      component="nav"
      sx={{
        p: 0,
        '& .MuiListItemIcon-root': {
          minWidth: 32,
          color: theme.palette.grey[500],
        },
      }}
    >
      <ListItemButton
        selected={selectedIndex === 0}
        onClick={() => handleListItemClick(0, 'changepassword')}
      >
        <ListItemIcon>
          <KeyOutlined />
        </ListItemIcon>
        <ListItemText primary="Change password" title="Change your password" />
      </ListItemButton>

      <ListItemButton
        selected={selectedIndex === 1}
        onClick={handleLogout}
        sx={{ color: themePalette.palette.error.main }}
      >
        <ListItemIcon>
          <LogoutOutlined style={{ color: themePalette.palette.error.main }} />
        </ListItemIcon>
        <ListItemText primary="Logout" title="Logout from the application" />
      </ListItemButton>
    </List>
  )
}
