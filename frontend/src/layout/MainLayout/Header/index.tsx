import React from 'react'
import {
  useTheme,
  AppBar,
  IconButton,
  Toolbar,
  useMediaQuery,
} from '@mui/material'
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons'

import { Profile } from 'layout/MainLayout/Header/Profile'
import { AppBarStyled } from './AppBarStyled'

interface HeaderProps {
  open: boolean
  handleDrawerToggle: () => void
}

export const Header = ({ open, handleDrawerToggle }: HeaderProps) => {
  const theme = useTheme()
  const matchDownLG = useMediaQuery(theme.breakpoints.down('lg'))

  const iconBackColor = 'grey.100'
  const iconBackColorOpen = 'grey.200'

  const mainHeader = (
    <Toolbar sx={{ justifyContent: 'space-between' }}>
      <IconButton
        disableRipple
        aria-label="open drawer"
        onClick={handleDrawerToggle}
        edge="start"
        color="secondary"
        sx={{
          color: 'text.primary',
          bgcolor: open ? iconBackColorOpen : iconBackColor,
          ml: { xs: 0, lg: -2 },
        }}
        title={open ? 'Collapse menu' : 'Expand menu'}
      >
        {!open ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      </IconButton>
      <Profile />
    </Toolbar>
  )

  const appBar = {
    position: 'fixed' as any,
    color: 'inherit' as any,
    elevation: 0,
    sx: {
      borderBottom: `1px solid ${theme.palette.divider}`,
    },
  }

  return !matchDownLG ? (
    <AppBarStyled
      open={open}
      theme={theme}
      position={appBar.position}
      color={appBar.color}
      elevation={appBar.elevation}
      sx={appBar.sx}
    >
      {mainHeader}
    </AppBarStyled>
  ) : (
    <AppBar
      position={appBar.position}
      color={appBar.color}
      elevation={appBar.elevation}
      sx={appBar.sx}
    >
      {mainHeader}
    </AppBar>
  )
}
