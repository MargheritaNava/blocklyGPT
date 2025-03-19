import React from 'react'
import { useTheme, Stack, Chip } from '@mui/material'

import { LogoSection } from 'components/Logo'
import { DrawerHeaderStyled } from './DrawerHeaderStyled'
import packageInfo from '../../../../../../package.json'

interface DrawerHeaderProps {
  open: boolean
}

export const DrawerHeader = ({ open }: DrawerHeaderProps) => {
  const theme = useTheme()

  return (
    <DrawerHeaderStyled theme={theme} open={open}>
      <Stack direction="row" spacing={1} alignItems="center">
        <LogoSection />
        <Chip
          label={packageInfo.version}
          size="small"
          title="BlocklyGPT version"
          sx={{
            height: 16,
            '& .MuiChip-label': { fontSize: '0.625rem', py: 0.25 },
          }}
          component="div"
        />
      </Stack>
    </DrawerHeaderStyled>
  )
}
