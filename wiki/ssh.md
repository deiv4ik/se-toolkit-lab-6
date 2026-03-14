# VM Information

## Connecting via SSH
To connect to your VM via SSH, follow these steps:

1. Get the VM IP address from your instructor or cloud provider
2. Open a terminal on your local machine
3. Run the SSH command with your username and the VM IP:4. If this is your first time connecting, you'll see a warning about authenticity. Type 'yes' to continue.
5. Enter your password when prompted (it won't show as you type)
6. You should now be logged into your VM

## SSH Key Authentication (Optional)
For more secure and convenient access, you can set up SSH keys:
1. Generate a key pair: `ssh-keygen -t ed25519`
2. Copy the public key to your VM: `ssh-copy-id operator@<vm-ip-address>`
3. Now you can log in without a password

## Troubleshooting
- If connection times out, check that the VM is running and the SSH port (22) is open
- If you get "Permission denied", verify your username and password
- If you get "Connection refused", SSH service might not be running on the VM
