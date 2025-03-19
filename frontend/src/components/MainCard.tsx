import React, { forwardRef, ReactNode, RefObject } from 'react'
import { useTheme, Button, Card, CardContent, CardHeader } from '@mui/material'

const headerSX = {
  p: 2.5,
  '& .MuiCardHeader-action': { m: '0px auto', alignSelf: 'center' },
}

export interface AdditionalAction {
  label: string
  action: () => void
}

interface MainCardProps {
  border?: boolean
  boxShadow?: boolean
  elevation?: number
  shadow?: string
  sx?: any
  title?: string
  subtitle?: string
  content?: boolean
  children?: ReactNode
  contentSX?: any
  backFunction?: any
  backTitle?: string
  additionalAction?: AdditionalAction[]
  customElement?: any
}

export const MainCard = forwardRef(
  (
    {
      border,
      boxShadow,
      elevation,
      shadow,
      sx,
      title,
      subtitle,
      content,
      children,
      contentSX,
      backFunction,
      backTitle,
      additionalAction,
      customElement,
    }: MainCardProps,
    ref,
  ) => {
    const theme = useTheme()
    const boxShadowThemed =
      theme.palette.mode === 'dark' ? boxShadow || true : boxShadow

    return (
      <Card
        elevation={elevation}
        ref={ref as RefObject<HTMLDivElement>}
        sx={{
          ...sx,
          border: border ? '1px solid' : 'none',
          borderRadius: 2,
          borderColor:
            theme.palette.mode === 'dark'
              ? theme.palette.divider
              : (theme.palette.grey as any).A800,
          boxShadow:
            boxShadowThemed && (!border || theme.palette.mode === 'dark')
              ? shadow || (theme as any).customShadows.z1
              : 'inherit',
          ':hover': {
            boxShadow: boxShadowThemed
              ? shadow || (theme as any).customShadows.z1
              : 'inherit',
          },
          '& pre': {
            m: 0,
            p: '16px !important',
            fontFamily: theme.typography.fontFamily,
            fontSize: '0.75rem',
          },
        }}
      >
        {/* card header and action */}
        {title && (
          <CardHeader
            sx={headerSX}
            title={title}
            titleTypographyProps={{ variant: 'h3' }}
            subheader={subtitle}
            subheaderTypographyProps={{ variant: 'h5' }}
            action={
              <>
                {additionalAction?.map((item) => (
                  <Button
                    key={item.label}
                    onClick={() => item.action()}
                    variant="outlined"
                    sx={{ marginRight: '0.5rem' }}
                  >
                    {item.label}
                  </Button>
                ))}
                {backFunction && (
                  <Button onClick={() => backFunction()} title={backTitle}>
                    Back
                  </Button>
                )}
                {customElement}
              </>
            }
          />
        )}

        {/* card content */}
        {content && <CardContent sx={contentSX}>{children}</CardContent>}
        {!content && children}
      </Card>
    )
  },
)

MainCard.displayName = 'MainCard'
MainCard.defaultProps = {
  border: true,
  boxShadow: false,
  elevation: 0,
  shadow: '',
  sx: {},
  title: '',
  subtitle: '',
  content: true,
  children: null,
  contentSX: {},
  backFunction: null,
  backTitle: '',
  additionalAction: [],
  customElement: null,
}
