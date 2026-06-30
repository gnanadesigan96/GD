import { cn } from '@/lib/cn'
import { HTMLAttributes } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {}

export function Card({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn('bg-white rounded-xl border border-amber-100 shadow-sm p-6', className)}
      {...props}
    >
      {children}
    </div>
  )
}
