# Security Group for Flink EC2 instance
resource "aws_security_group" "flink_sg" {
  name        = "${var.project_name}-flink-sg"
  description = "Security group for Flink streaming job server"
  vpc_id      = aws_vpc.main.id

  # SSH access from your IP
  ingress {
    description = "SSH from authorized IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_address]
  }

  # Flink Web UI access from your IP
  ingress {
    description = "Flink Web UI from authorized IP"
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_address]
  }

  # Flink JobManager port
  ingress {
    description = "Flink JobManager from VPC"
    from_port   = 6123
    to_port     = 6123
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # Flink TaskManager port
  ingress {
    description = "Flink TaskManager from VPC"
    from_port   = 6124
    to_port     = 6124
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  # Allow outbound traffic to MSK
  egress {
    description     = "Access to MSK cluster"
    from_port       = 9092
    to_port         = 9098
    protocol        = "tcp"
    security_groups = [aws_security_group.msk.id]
  }

  # Allow outbound traffic to ECS tasks for API calls
  egress {
    description     = "Access to FastAPI service"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # All other outbound traffic allowed
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-flink-sg"
    Environment = var.environment
    Purpose     = "Flink streaming job server security group"
  }
}

# IAM role for Flink EC2 instance
resource "aws_iam_role" "flink_role" {
  name = "${var.project_name}-flink-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-flink-role"
    Environment = var.environment
    Purpose     = "Flink streaming job server IAM role"
  }
}

# IAM policy for Flink MSK access
resource "aws_iam_role_policy" "flink_msk_policy" {
  name = "${var.project_name}-flink-msk-policy"
  role = aws_iam_role.flink_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kafka-cluster:Connect",
          "kafka-cluster:AlterCluster",
          "kafka-cluster:DescribeCluster",
          "kafka-cluster:*Topic*",
          "kafka-cluster:WriteData",
          "kafka-cluster:ReadData",
          "kafka-cluster:AlterGroup",
          "kafka-cluster:DescribeGroup"
        ]
        Resource = [
          aws_msk_cluster.main.arn,
          "${aws_msk_cluster.main.arn}/*"
        ]
      }
    ]
  })
}

# IAM policy for Flink CloudWatch Logs access
resource "aws_iam_role_policy" "flink_cloudwatch_policy" {
  name = "${var.project_name}-flink-cloudwatch-policy"
  role = aws_iam_role.flink_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# IAM instance profile for Flink server
resource "aws_iam_instance_profile" "flink_profile" {
  name = "${var.project_name}-flink-profile"
  role = aws_iam_role.flink_role.name
}

# User data script for Flink server
locals {
  flink_user_data = <<-EOF
#!/bin/bash
# Update system and install Java
yum update -y
yum install -y java-11-amazon-corretto-headless wget unzip

# Create Flink user
useradd -m -s /bin/bash flink
usermod -a -G flink ec2-user

# Download and install Flink
cd /opt
wget https://archive.apache.org/dist/flink/flink-1.17.2/flink-1.17.2-bin-scala_2.12.tgz
tar -xzf flink-1.17.2-bin-scala_2.12.tgz
ln -s flink-1.17.2 flink
chown -R flink:flink /opt/flink*

# Configure Flink
cat > /opt/flink/conf/flink-conf.yaml <<'FLINK_CONFIG'
jobmanager.rpc.address: localhost
jobmanager.rpc.port: 6123
jobmanager.memory.process.size: 1600m
taskmanager.memory.process.size: 1728m
taskmanager.numberOfTaskSlots: 1
parallelism.default: 1
rest.bind-port: 8081
rest.address: 0.0.0.0
FLINK_CONFIG

# Configure Flink environment
cat > /opt/flink/conf/workers <<'WORKERS'
localhost
WORKERS

# Set up Flink as a systemd service
cat > /etc/systemd/system/flink-jobmanager.service <<'JOBMANAGER_SERVICE'
[Unit]
Description=Flink JobManager
After=network.target

[Service]
Type=forking
User=flink
Group=flink
Environment=JAVA_HOME=/usr/lib/jvm/java-11-amazon-corretto
ExecStart=/opt/flink/bin/jobmanager.sh start
ExecStop=/opt/flink/bin/jobmanager.sh stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
JOBMANAGER_SERVICE

cat > /etc/systemd/system/flink-taskmanager.service <<'TASKMANAGER_SERVICE'
[Unit]
Description=Flink TaskManager
After=network.target flink-jobmanager.service

[Service]
Type=forking
User=flink
Group=flink
Environment=JAVA_HOME=/usr/lib/jvm/java-11-amazon-corretto
ExecStart=/opt/flink/bin/taskmanager.sh start
ExecStop=/opt/flink/bin/taskmanager.sh stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
TASKMANAGER_SERVICE

# Enable and start Flink services
systemctl daemon-reload
systemctl enable flink-jobmanager
systemctl enable flink-taskmanager
systemctl start flink-jobmanager
systemctl start flink-taskmanager

# Create directory for Flink job files
mkdir -p /opt/flink/usrlib
chown -R flink:flink /opt/flink/usrlib

# Set up basic firewall rules
systemctl enable firewalld
systemctl start firewalld
firewall-cmd --permanent --add-port=22/tcp
firewall-cmd --permanent --add-port=8081/tcp
firewall-cmd --permanent --add-port=6123/tcp
firewall-cmd --permanent --add-port=6124/tcp
firewall-cmd --reload

echo "Flink server setup completed!"
echo "Flink Web UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8081"
echo ""
echo "To submit a Flink job:"
echo "1. Copy your flink_job.py to /opt/flink/usrlib/"
echo "2. Run: flink run /opt/flink/usrlib/flink_job.py"
EOF
}

# EC2 instance for Flink streaming job server
resource "aws_instance" "flink_instance" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = var.flink_instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.flink_sg.id]
  subnet_id              = aws_subnet.public[0].id
  iam_instance_profile   = aws_iam_instance_profile.flink_profile.name
  user_data              = local.flink_user_data

  root_block_device {
    volume_size = 30
    volume_type = "gp3"
    encrypted   = true
  }

  tags = {
    Name        = "${var.project_name}-flink-server"
    Environment = var.environment
    Purpose     = "Flink streaming job server"
    Service     = "flink"
  }

  depends_on = [
    aws_security_group.flink_sg,
    aws_security_group.msk,
    aws_security_group.ecs_tasks
  ]
}

# Elastic IP for Flink server (for stable public IP)
resource "aws_eip" "flink_eip" {
  instance = aws_instance.flink_instance.id
  domain   = "vpc"

  tags = {
    Name        = "${var.project_name}-flink-server-eip"
    Environment = var.environment
    Purpose     = "Flink streaming job server static IP"
  }
}
