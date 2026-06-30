module.exports = {
  apps: [
    {
      name: 'morningbell',
      script: 'npm',
      args: 'start',
      cwd: '/home/morningbell/morningbell',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
      error_file: '/home/morningbell/logs/morningbell-error.log',
      out_file: '/home/morningbell/logs/morningbell-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
}
