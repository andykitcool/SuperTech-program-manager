import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect('49.233.213.245', username='root', password='Hongmei1982', timeout=30, banner_timeout=120)
    
    # 启动容器
    print("\n=== Starting containers ===")
    stdin, stdout, stderr = ssh.exec_command("cd /root/supertech-program-manager_new && docker compose up -d 2>&1", timeout=60)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print(out)
    if err:
        print("ERR:", err[:1000])
    
    # 等待容器启动
    time.sleep(5)
    
    # 检查状态
    print("\n=== Container status ===")
    stdin, stdout, stderr = ssh.exec_command("docker ps --format 'table {{.Names}}\\t{{.Status}}'", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # 检查 SSL 文件是否在 volume 中
    print("\n=== SSL files in web container ===")
    stdin, stdout, stderr = ssh.exec_command("docker exec supertech-program-manager_new-web-1 ls -la /etc/nginx/ssl/ 2>&1", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    print("\n=== Nginx conf files ===")
    stdin, stdout, stderr = ssh.exec_command("docker exec supertech-program-manager_new-web-1 ls -la /etc/nginx/network/ 2>&1", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # 检查 SSL conf 内容
    print("\n=== SSL conf content ===")
    stdin, stdout, stderr = ssh.exec_command("docker exec supertech-program-manager_new-web-1 cat /etc/nginx/network/ssl.conf 2>&1", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # 测试 HTTPS
    print("\n=== Test HTTPS ===")
    stdin, stdout, stderr = ssh.exec_command("curl -sk --max-time 5 https://127.0.0.1:443/ -o /dev/null -w '%{http_code}' 2>&1", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
    # 测试 HTTP
    print("\n=== Test HTTP ===")
    stdin, stdout, stderr = ssh.exec_command("curl -s --max-time 5 http://127.0.0.1:3000/ -o /dev/null -w '%{http_code}' 2>&1", timeout=15)
    print(stdout.read().decode('utf-8', errors='replace'))
    
except Exception as e:
    print(f'Error: {e}')
finally:
    ssh.close()
