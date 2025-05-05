
# Home Assistant S3 Storage Backup Integration

This custom integration allows you to backup your Home Assistant instance to any S3-compatible storage service, such as AWS S3, MinIO, DigitalOcean Spaces, or any other S3-compatible storage provider.

## Features

- Backup to any S3-compatible storage service
- Configurable endpoint URL for custom S3-compatible services
- Secure storage of credentials
- Automatic backup management
- Full integration with Home Assistant's backup system

## Prerequisites

- Home Assistant instance
- S3-compatible storage service credentials:
  - Access Key ID
  - Secret Access Key
  - Bucket name
  - Endpoint URL (optional, for custom S3-compatible services)

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the "+" button
4. Search for "S3 Storage"
5. Click "Download"
6. Restart Home Assistant

### Manual Installation

1. Download the latest release from the GitHub repository
2. Copy the `s3_storage` folder to your `custom_components` directory
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click the "+ ADD INTEGRATION" button
3. Search for "S3 Storage"
4. Fill in the required information:
   - Access Key ID
   - Secret Access Key
   - Bucket Name
   - Endpoint URL (optional)

## Usage

Once configured, the integration will appear as a backup target in your Home Assistant backup interface. You can:

- Create new backups directly to S3
- View existing backups stored in S3
- Restore backups from S3
- Delete backups from S3

## Troubleshooting

### Common Issues

1. **Connection Failed**: Verify your endpoint URL and credentials are correct
2. **Permission Denied**: Ensure your S3 bucket permissions are properly configured
3. **Backup Failed**: Check your Home Assistant logs for detailed error messages

## Technical Details

- Built with `aioboto3` for asynchronous S3 operations
- Fully integrated with Home Assistant's backup system
- Supports metadata versioning for backup compatibility
- Implements efficient chunked upload/download

## Requirements

- Home Assistant Core 2023.8.0 or newer
- Python 3.11 or newer
- `boto3==1.38.8`
- `aioboto3==14.1.0`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## Credits

Created and maintained by [@sopleb](https://github.com/sopleb)

## Support

- Report issues via [GitHub Issues](https://github.com/sopleb/s3_storage/issues)
- Ask questions in the [Home Assistant Community](https://community.home-assistant.io/)

---

For more information, visit the [documentation](https://github.com/sopleb/s3_storage).