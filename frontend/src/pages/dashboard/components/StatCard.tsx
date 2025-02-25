import React from 'react'
import { Card, CardContent, Typography, Box, CircularProgress } from '@mui/material'

interface StatCardProps {
  title: string
  value: number | string
  icon?: React.ReactNode
  color?: string
  loading?: boolean
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color = 'primary.main',
  loading = false
}) => {
  return (
    <Card className="w-full min-w-[200px]">
      <CardContent className="flex items-center p-4">
        {icon && (
          <Box
            className="flex items-center justify-center rounded-full p-2 mr-3"
            sx={{ bgcolor: `${color}20`, color }}
          >
            {icon}
          </Box>
        )}
        <Box className="flex-grow">
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          {loading ? (
            <CircularProgress size={20} />
          ) : (
            <Typography variant="h5" component="div" fontWeight="bold">
              {value}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  )
} 