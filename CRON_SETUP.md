# Job Statistics Cron Setup Guide

This guide explains how to set up automated daily updates for job statistics using cron.

## Prerequisites

- KIGate application installed and configured
- Python 3.7+ installed
- Write access to system logs (or use user-specific log location)

## Quick Setup

### 1. Test the CLI Script

First, verify that the statistics script works correctly:

```bash
cd /path/to/KIGate
python3 cli_update_statistics.py
```

Expected output:
```
2025-11-11 15:41:20 - __main__ - INFO - KIGate Job Statistics Update Script
2025-11-11 15:41:20 - __main__ - INFO - Started at: 2025-11-11 15:41:20
...
2025-11-11 15:41:20 - __main__ - INFO - Statistics update completed successfully:
2025-11-11 15:41:20 - __main__ - INFO -   - Daily statistics: X records
2025-11-11 15:41:20 - __main__ - INFO -   - Weekly statistics: X records
2025-11-11 15:41:20 - __main__ - INFO -   - Monthly statistics: X records
```

### 2. Set Up Log Directory (Optional)

Create a dedicated log directory:

```bash
sudo mkdir -p /var/log/kigate
sudo chown $USER:$USER /var/log/kigate
```

Or use a user-specific directory:

```bash
mkdir -p ~/logs/kigate
```

### 3. Edit Crontab

Open your crontab editor:

```bash
crontab -e
```

### 4. Add Cron Job Entry

Add one of the following lines based on your preference:

#### Daily at 1:00 AM (Recommended)
```bash
0 1 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate/stats.log 2>&1
```

#### Daily at 2:30 AM
```bash
30 2 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate/stats.log 2>&1
```

#### Every 6 hours
```bash
0 */6 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate/stats.log 2>&1
```

#### User-specific log location
```bash
0 1 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> ~/logs/kigate/stats.log 2>&1
```

**Note:** Replace `/path/to/KIGate` with the actual path to your KIGate installation.

### 5. Verify Cron Job

List your cron jobs to verify:

```bash
crontab -l
```

## Cron Schedule Format

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday = 0)
│ │ │ │ │
* * * * * command to execute
```

### Common Schedules

| Schedule | Cron Expression | Description |
|----------|----------------|-------------|
| Daily at midnight | `0 0 * * *` | Every day at 00:00 |
| Daily at 1 AM | `0 1 * * *` | Every day at 01:00 |
| Every 12 hours | `0 */12 * * *` | At 00:00 and 12:00 |
| Every 6 hours | `0 */6 * * *` | At 00:00, 06:00, 12:00, 18:00 |
| Weekly on Sunday | `0 2 * * 0` | Every Sunday at 02:00 |

## Monitoring

### View Recent Logs

```bash
tail -f /var/log/kigate/stats.log
```

Or for user-specific logs:

```bash
tail -f ~/logs/kigate/stats.log
```

### Check Last Run Status

```bash
tail -20 /var/log/kigate/stats.log | grep -E "(Status|Duration|records)"
```

### Log Rotation (Optional)

To prevent log files from growing too large, set up log rotation:

Create `/etc/logrotate.d/kigate-stats`:

```
/var/log/kigate/stats.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 0644 your-user your-group
}
```

Test the configuration:

```bash
sudo logrotate -d /etc/logrotate.d/kigate-stats
```

## Troubleshooting

### Cron Job Not Running

1. **Check cron service status:**
   ```bash
   sudo systemctl status cron
   ```

2. **Check system mail for errors:**
   ```bash
   mail
   ```

3. **Verify Python path:**
   ```bash
   which python3
   ```
   Update the cron command with the correct path if needed.

### Permission Issues

If you encounter permission errors:

```bash
# Make script executable
chmod +x /path/to/KIGate/cli_update_statistics.py

# Check file ownership
ls -l /path/to/KIGate/cli_update_statistics.py

# Fix if needed
chown $USER:$USER /path/to/KIGate/cli_update_statistics.py
```

### Database Lock Issues

If you encounter "database is locked" errors:

1. Ensure the application server isn't running during cron execution
2. Or schedule the cron job during low-traffic periods
3. Consider using a more robust database if SQLite locking becomes an issue

### Virtual Environment

If you're using a virtual environment, activate it in the cron command:

```bash
0 1 * * * cd /path/to/KIGate && source venv/bin/activate && python cli_update_statistics.py >> /var/log/kigate/stats.log 2>&1
```

## Alternative: Systemd Timer

For systems using systemd, you can use a timer instead of cron:

### 1. Create Service File

Create `/etc/systemd/system/kigate-stats.service`:

```ini
[Unit]
Description=KIGate Statistics Update
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/KIGate
ExecStart=/usr/bin/python3 cli_update_statistics.py
StandardOutput=append:/var/log/kigate/stats.log
StandardError=append:/var/log/kigate/stats.log
```

### 2. Create Timer File

Create `/etc/systemd/system/kigate-stats.timer`:

```ini
[Unit]
Description=Run KIGate Statistics Update Daily
Requires=kigate-stats.service

[Timer]
OnCalendar=daily
OnCalendar=01:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 3. Enable and Start Timer

```bash
sudo systemctl daemon-reload
sudo systemctl enable kigate-stats.timer
sudo systemctl start kigate-stats.timer
```

### 4. Check Timer Status

```bash
sudo systemctl list-timers --all | grep kigate
sudo systemctl status kigate-stats.timer
```

## Best Practices

1. **Schedule during low-traffic periods** to minimize impact on the database
2. **Monitor log files regularly** to catch issues early
3. **Set up log rotation** to prevent disk space issues
4. **Test manually** before setting up cron to ensure everything works
5. **Keep logs for troubleshooting** but don't let them grow indefinitely
6. **Use absolute paths** in cron commands to avoid path-related issues
7. **Consider email notifications** for cron job failures

## Email Notifications

To receive email notifications for cron job output:

1. **Set MAILTO in crontab:**
   ```bash
   MAILTO=your-email@example.com
   0 1 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate/stats.log 2>&1
   ```

2. **Or use a wrapper script to send notifications:**
   ```bash
   #!/bin/bash
   OUTPUT=$(cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py 2>&1)
   if [ $? -ne 0 ]; then
       echo "$OUTPUT" | mail -s "KIGate Stats Update Failed" your-email@example.com
   fi
   ```

## Support

For issues or questions:
- Check the main documentation: [JOB_STATISTICS_DOCUMENTATION.md](JOB_STATISTICS_DOCUMENTATION.md)
- Review application logs
- Test the script manually to isolate issues
