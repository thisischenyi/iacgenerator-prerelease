# Excel模板字段定义规范 - MVP阶段

## 目录
- [通用说明](#通用说明)
- [AWS资源定义](#aws资源定义)
  - [AWS_EC2](#aws_ec2)
  - [AWS_VPC](#aws_vpc)
  - [AWS_Subnet](#aws_subnet)
  - [AWS_SecurityGroup](#aws_securitygroup)
  - [AWS_S3](#aws_s3)
  - [AWS_RDS](#aws_rds)
- [Azure资源定义](#azure资源定义)
  - [Azure_VM](#azure_vm)
  - [Azure_VNet](#azure_vnet)
  - [Azure_Subnet](#azure_subnet)
  - [Azure_NSG](#azure_nsg)
  - [Azure_Storage](#azure_storage)
  - [Azure_SQL](#azure_sql)
- [数据验证规则](#数据验证规则)
- [JSON格式字段Schema](#json格式字段schema)

---

## 通用说明

### 字段属性标注
- **[必填]**: 必须提供值
- **[可选]**: 可以为空，系统会使用默认值或跳过
- **[下拉]**: 提供下拉选项的字段
- **[JSON]**: 需要填写JSON格式的字段
- **[引用]**: 引用其他资源的字段

### 通用列
所有资源Sheet都包含以下通用列：

| 列名 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| ResourceName | 文本 | [必填] | 资源唯一标识名称 | web-server-01 |
| Environment | 下拉 | [必填] | 环境类型 | Production |
| Project | 文本 | [必填] | 项目名称 | ecommerce-platform |
| Owner | 文本 | [可选] | 资源负责人 | john.doe@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心代码 | CC-12345 |
| Tags | JSON | [可选] | 自定义标签 | {"Department": "IT", "Compliance": "PCI"} |

**Environment下拉选项**:
- Development
- Testing
- Staging
- Production
- DR (Disaster Recovery)

---

## AWS资源定义

### AWS_EC2

**用途**: 定义AWS EC2虚拟机实例

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | EC2实例名称 | 字母数字-_ | web-server-01 |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| Region | 下拉 | [必填] | AWS区域 | 见AWS区域列表 | us-east-1 |
| AvailabilityZone | 下拉 | [可选] | 可用区 | 必须在所选Region内 | us-east-1a |
| InstanceType | 下拉 | [必填] | 实例类型 | 见EC2实例类型 | t3.medium |
| AMI_ID | 文本 | [必填] | AMI镜像ID | ami-xxxxxxxx格式 | ami-0c55b159cbfafe1f0 |
| VPC_Reference | 引用 | [必填] | VPC引用名称 | 必须存在于AWS_VPC | main-vpc |
| Subnet_Reference | 引用 | [必填] | 子网引用名称 | 必须存在于AWS_Subnet | private-subnet-1 |
| SecurityGroups | 引用列表 | [必填] | 安全组引用 | 逗号分隔，必须存在 | web-sg,common-sg |
| KeyPairName | 文本 | [必填] | SSH密钥对名称 | - | my-keypair |
| AssociatePublicIP | 下拉 | [必填] | 是否分配公网IP | true/false | false |
| RootVolumeSize | 数字 | [必填] | 根卷大小(GB) | 8-16384 | 30 |
| RootVolumeType | 下拉 | [必填] | 根卷类型 | gp3/gp2/io1/io2 | gp3 |
| EnableMonitoring | 下拉 | [可选] | 启用详细监控 | true/false，默认false | true |
| UserData | 文本 | [可选] | 用户数据脚本 | Base64或纯文本 | #!/bin/bash\napt update |
| IAM_Role | 文本 | [可选] | IAM角色名称 | - | ec2-s3-access-role |
| Owner | 文本 | [可选] | 负责人 | - | john.doe@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Application": "WebServer"} |

**AWS区域下拉选项**:
```
us-east-1, us-east-2, us-west-1, us-west-2
eu-west-1, eu-central-1, ap-southeast-1, ap-northeast-1
```

**EC2实例类型下拉选项** (常用):
```
t3.micro, t3.small, t3.medium, t3.large, t3.xlarge
m5.large, m5.xlarge, m5.2xlarge
c5.large, c5.xlarge, r5.large, r5.xlarge
```

---

### AWS_VPC

**用途**: 定义AWS虚拟私有云

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | VPC名称 | 字母数字-_ | main-vpc |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| Region | 下拉 | [必填] | AWS区域 | 见AWS区域列表 | us-east-1 |
| CIDR_Block | 文本 | [必填] | CIDR地址块 | 有效CIDR格式 | 10.0.0.0/16 |
| EnableDNSHostnames | 下拉 | [必填] | 启用DNS主机名 | true/false | true |
| EnableDNSSupport | 下拉 | [必填] | 启用DNS解析 | true/false | true |
| InstanceTenancy | 下拉 | [可选] | 实例租赁 | default/dedicated | default |
| Owner | 文本 | [可选] | 负责人 | - | network-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"NetworkType": "Production"} |

**CIDR验证规则**:
- 必须是有效的CIDR表示法
- 推荐使用RFC 1918私有地址范围: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- 最小网络掩码: /16，最大: /28

---

### AWS_Subnet

**用途**: 定义AWS子网

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 子网名称 | 字母数字-_ | private-subnet-1 |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| VPC_Reference | 引用 | [必填] | VPC引用名称 | 必须存在于AWS_VPC | main-vpc |
| AvailabilityZone | 下拉 | [必填] | 可用区 | 必须在VPC的Region内 | us-east-1a |
| CIDR_Block | 文本 | [必填] | CIDR地址块 | 必须在VPC CIDR范围内 | 10.0.1.0/24 |
| MapPublicIP | 下拉 | [必填] | 自动分配公网IP | true/false | false |
| SubnetType | 下拉 | [必填] | 子网类型 | Public/Private | Private |
| Owner | 文本 | [可选] | 负责人 | - | network-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Tier": "Application"} |

**SubnetType说明**:
- **Public**: 通常配合Internet Gateway，MapPublicIP=true
- **Private**: 用于内部资源，MapPublicIP=false

---

### AWS_SecurityGroup

**用途**: 定义AWS安全组

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 安全组名称 | 字母数字-_ | web-sg |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| VPC_Reference | 引用 | [必填] | VPC引用名称 | 必须存在于AWS_VPC | main-vpc |
| Description | 文本 | [必填] | 安全组描述 | - | Security group for web servers |
| IngressRules | JSON | [必填] | 入站规则 | 见JSON Schema | 见下方示例 |
| EgressRules | JSON | [可选] | 出站规则 | 见JSON Schema，默认允许全部 | 见下方示例 |
| Owner | 文本 | [可选] | 负责人 | - | security-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"SecurityLevel": "High"} |

**IngressRules JSON示例**:
```json
[
  {
    "protocol": "tcp",
    "from_port": 443,
    "to_port": 443,
    "cidr_blocks": ["0.0.0.0/0"],
    "description": "HTTPS from anywhere"
  },
  {
    "protocol": "tcp",
    "from_port": 22,
    "to_port": 22,
    "cidr_blocks": ["10.0.0.0/16"],
    "description": "SSH from VPC only"
  }
]
```

**EgressRules JSON示例**:
```json
[
  {
    "protocol": "-1",
    "from_port": 0,
    "to_port": 0,
    "cidr_blocks": ["0.0.0.0/0"],
    "description": "Allow all outbound"
  }
]
```

---

### AWS_S3

**用途**: 定义AWS S3存储桶

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 存储桶名称 | 全局唯一，小写字母数字- | my-app-data-bucket-2026 |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| Region | 下拉 | [必填] | AWS区域 | 见AWS区域列表 | us-east-1 |
| Versioning | 下拉 | [必填] | 启用版本控制 | Enabled/Suspended | Enabled |
| Encryption | 下拉 | [必填] | 加密方式 | AES256/aws:kms | AES256 |
| KMS_Key_ID | 文本 | [可选] | KMS密钥ID | 当Encryption=aws:kms时必填 | arn:aws:kms:us-east-1:... |
| BlockPublicAccess | 下拉 | [必填] | 阻止公共访问 | true/false | true |
| BucketPolicy | JSON | [可选] | 存储桶策略 | 有效IAM策略JSON | 见下方示例 |
| LifecycleRules | JSON | [可选] | 生命周期规则 | 见JSON Schema | 见下方示例 |
| Owner | 文本 | [可选] | 负责人 | - | storage-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"DataClassification": "Confidential"} |

**存储桶命名规则**:
- 3-63个字符
- 只能包含小写字母、数字、连字符(-)和点(.)
- 必须以字母或数字开头和结尾
- 全局唯一

**LifecycleRules JSON示例**:
```json
[
  {
    "id": "archive-old-logs",
    "status": "Enabled",
    "transitions": [
      {
        "days": 30,
        "storage_class": "STANDARD_IA"
      },
      {
        "days": 90,
        "storage_class": "GLACIER"
      }
    ],
    "expiration": {
      "days": 365
    }
  }
]
```

---

### AWS_RDS

**用途**: 定义AWS RDS关系型数据库

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 数据库实例名称 | 字母数字-_ | prod-mysql-db |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| Region | 下拉 | [必填] | AWS区域 | 见AWS区域列表 | us-east-1 |
| Engine | 下拉 | [必填] | 数据库引擎 | 见引擎列表 | mysql |
| EngineVersion | 文本 | [必填] | 引擎版本 | 依赖Engine | 8.0.35 |
| InstanceClass | 下拉 | [必填] | 实例类型 | 见RDS实例类型 | db.t3.medium |
| AllocatedStorage | 数字 | [必填] | 存储空间(GB) | 20-65536 | 100 |
| StorageType | 下拉 | [必填] | 存储类型 | gp3/gp2/io1 | gp3 |
| StorageEncrypted | 下拉 | [必填] | 启用加密 | true/false | true |
| KMS_Key_ID | 文本 | [可选] | KMS密钥ID | 当StorageEncrypted=true时可选 | arn:aws:kms:... |
| DBName | 文本 | [必填] | 初始数据库名 | 字母数字_ | ecommerce_db |
| MasterUsername | 文本 | [必填] | 主用户名 | 字母开头，字母数字_ | admin |
| MasterPassword | 文本 | [必填] | 主密码 | 8-41字符，不含@/" | 请使用强密码 |
| VPC_Reference | 引用 | [必填] | VPC引用名称 | 必须存在于AWS_VPC | main-vpc |
| SubnetGroup_Subnets | 引用列表 | [必填] | 子网引用列表 | 逗号分隔，至少2个不同AZ | private-subnet-1,private-subnet-2 |
| SecurityGroups | 引用列表 | [必填] | 安全组引用 | 逗号分隔 | db-sg |
| MultiAZ | 下拉 | [必填] | 多可用区部署 | true/false | true |
| PubliclyAccessible | 下拉 | [必填] | 公网访问 | true/false | false |
| BackupRetentionPeriod | 数字 | [必填] | 备份保留天数 | 0-35 | 7 |
| PreferredBackupWindow | 文本 | [可选] | 备份时间窗口 | HH:MM-HH:MM格式 | 03:00-04:00 |
| PreferredMaintenanceWindow | 文本 | [可选] | 维护时间窗口 | ddd:HH:MM-ddd:HH:MM | sun:04:00-sun:05:00 |
| AutoMinorVersionUpgrade | 下拉 | [可选] | 自动小版本升级 | true/false，默认true | false |
| DeletionProtection | 下拉 | [必填] | 删除保护 | true/false | true |
| Owner | 文本 | [可选] | 负责人 | - | dba-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Criticality": "High"} |

**Engine下拉选项**:
```
mysql, postgres, mariadb, oracle-ee, oracle-se2, sqlserver-ex, sqlserver-web, sqlserver-se, sqlserver-ee
```

**RDS实例类型下拉选项** (常用):
```
db.t3.micro, db.t3.small, db.t3.medium, db.t3.large
db.m5.large, db.m5.xlarge, db.m5.2xlarge
db.r5.large, db.r5.xlarge, db.r5.2xlarge
```

---

## Azure资源定义

### Azure_VM

**用途**: 定义Azure虚拟机

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 虚拟机名称 | 字母数字-_ | vm-web-prod-eastus-01 |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| ResourceGroup | 文本 | [必填] | 资源组名称 | - | rg-ecommerce-prod |
| Location | 下拉 | [必填] | Azure区域 | 见Azure区域列表 | eastus |
| VMSize | 下拉 | [必填] | 虚拟机大小 | 见Azure VM大小 | Standard_D2s_v3 |
| OSType | 下拉 | [必填] | 操作系统类型 | Linux/Windows | Linux |
| ImagePublisher | 文本 | [必填] | 镜像发布者 | - | Canonical |
| ImageOffer | 文本 | [必填] | 镜像产品 | - | UbuntuServer |
| ImageSKU | 文本 | [必填] | 镜像SKU | - | 18.04-LTS |
| ImageVersion | 文本 | [可选] | 镜像版本 | 默认latest | latest |
| VNet_Reference | 引用 | [必填] | 虚拟网络引用 | 必须存在于Azure_VNet | vnet-main |
| Subnet_Reference | 引用 | [必填] | 子网引用 | 必须存在于Azure_Subnet | subnet-app |
| NSG_Reference | 引用 | [可选] | NSG引用 | 必须存在于Azure_NSG | nsg-web |
| AdminUsername | 文本 | [必填] | 管理员用户名 | - | azureadmin |
| AuthenticationType | 下拉 | [必填] | 认证方式 | Password/SSH | SSH |
| AdminPassword | 文本 | [可选] | 管理员密码 | AuthType=Password时必填 | 请使用强密码 |
| SSHPublicKey | 文本 | [可选] | SSH公钥 | AuthType=SSH时必填 | ssh-rsa AAAAB3... |
| OSDiskType | 下拉 | [必填] | OS磁盘类型 | StandardSSD_LRS/Premium_LRS/Standard_LRS | Premium_LRS |
| OSDiskSizeGB | 数字 | [可选] | OS磁盘大小 | 30-2048，默认根据镜像 | 128 |
| DataDisks | JSON | [可选] | 数据磁盘配置 | 见JSON Schema | 见下方示例 |
| AssignPublicIP | 下拉 | [必填] | 分配公网IP | true/false | false |
| AvailabilityZone | 下拉 | [可选] | 可用性区域 | 1/2/3 | 1 |
| Owner | 文本 | [可选] | 负责人 | - | john.doe@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Application": "WebServer"} |

**Azure区域下拉选项**:
```
eastus, eastus2, westus, westus2, centralus
northeurope, westeurope, uksouth, southeastasia, eastasia
```

**Azure VM大小下拉选项** (常用):
```
Standard_B2s, Standard_B2ms, Standard_D2s_v3, Standard_D4s_v3
Standard_E2s_v3, Standard_E4s_v3, Standard_F2s_v2, Standard_F4s_v2
```

**DataDisks JSON示例**:
```json
[
  {
    "lun": 0,
    "diskSizeGB": 128,
    "storageAccountType": "Premium_LRS",
    "caching": "ReadWrite"
  },
  {
    "lun": 1,
    "diskSizeGB": 256,
    "storageAccountType": "StandardSSD_LRS",
    "caching": "ReadOnly"
  }
]
```

---

### Azure_VNet

**用途**: 定义Azure虚拟网络

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 虚拟网络名称 | 字母数字-_ | vnet-main |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| ResourceGroup | 文本 | [必填] | 资源组名称 | - | rg-ecommerce-prod |
| Location | 下拉 | [必填] | Azure区域 | 见Azure区域列表 | eastus |
| AddressSpace | 文本 | [必填] | 地址空间 | CIDR格式，可多个逗号分隔 | 10.0.0.0/16 |
| DNSServers | 文本 | [可选] | DNS服务器 | IP地址，逗号分隔 | 10.0.0.4,10.0.0.5 |
| Owner | 文本 | [可选] | 负责人 | - | network-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"NetworkType": "Production"} |

---

### Azure_Subnet

**用途**: 定义Azure子网

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 子网名称 | 字母数字-_ | subnet-app |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| VNet_Reference | 引用 | [必填] | 虚拟网络引用 | 必须存在于Azure_VNet | vnet-main |
| AddressPrefix | 文本 | [必填] | 地址前缀 | 必须在VNet地址空间内 | 10.0.1.0/24 |
| ServiceEndpoints | 文本 | [可选] | 服务终结点 | 逗号分隔 | Microsoft.Storage,Microsoft.Sql |
| Owner | 文本 | [可选] | 负责人 | - | network-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Tier": "Application"} |

**ServiceEndpoints选项**:
```
Microsoft.Storage, Microsoft.Sql, Microsoft.KeyVault, Microsoft.ServiceBus, Microsoft.EventHub
```

---

### Azure_NSG

**用途**: 定义Azure网络安全组

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | NSG名称 | 字母数字-_ | nsg-web |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| ResourceGroup | 文本 | [必填] | 资源组名称 | - | rg-ecommerce-prod |
| Location | 下拉 | [必填] | Azure区域 | 见Azure区域列表 | eastus |
| SecurityRules | JSON | [必填] | 安全规则 | 见JSON Schema | 见下方示例 |
| Owner | 文本 | [可选] | 负责人 | - | security-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"SecurityLevel": "High"} |

**SecurityRules JSON示例**:
```json
[
  {
    "name": "Allow-HTTPS",
    "priority": 100,
    "direction": "Inbound",
    "access": "Allow",
    "protocol": "Tcp",
    "sourcePortRange": "*",
    "destinationPortRange": "443",
    "sourceAddressPrefix": "Internet",
    "destinationAddressPrefix": "*",
    "description": "Allow HTTPS from Internet"
  },
  {
    "name": "Deny-SSH",
    "priority": 200,
    "direction": "Inbound",
    "access": "Deny",
    "protocol": "Tcp",
    "sourcePortRange": "*",
    "destinationPortRange": "22",
    "sourceAddressPrefix": "Internet",
    "destinationAddressPrefix": "*",
    "description": "Deny SSH from Internet"
  }
]
```

---

### Azure_Storage

**用途**: 定义Azure存储账户

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 存储账户名称 | 3-24字符，仅小写字母和数字，全局唯一 | stecommerceprod01 |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| ResourceGroup | 文本 | [必填] | 资源组名称 | - | rg-ecommerce-prod |
| Location | 下拉 | [必填] | Azure区域 | 见Azure区域列表 | eastus |
| AccountKind | 下拉 | [必填] | 账户类型 | StorageV2/BlobStorage/FileStorage | StorageV2 |
| AccountTier | 下拉 | [必填] | 性能层级 | Standard/Premium | Standard |
| ReplicationType | 下拉 | [必填] | 复制类型 | LRS/GRS/RAGRS/ZRS/GZRS/RAGZRS | GRS |
| AccessTier | 下拉 | [可选] | 访问层 | Hot/Cool，默认Hot | Hot |
| EnableHTTPSOnly | 下拉 | [必填] | 仅HTTPS访问 | true/false | true |
| MinimumTLSVersion | 下拉 | [必填] | 最小TLS版本 | TLS1_0/TLS1_1/TLS1_2 | TLS1_2 |
| AllowBlobPublicAccess | 下拉 | [必填] | 允许Blob公共访问 | true/false | false |
| EnableBlobEncryption | 下拉 | [必填] | Blob加密 | true/false | true |
| EnableFileEncryption | 下拉 | [必填] | 文件加密 | true/false | true |
| NetworkRules | JSON | [可选] | 网络规则 | 见JSON Schema | 见下方示例 |
| BlobContainers | JSON | [可选] | Blob容器配置 | 见JSON Schema | 见下方示例 |
| Owner | 文本 | [可选] | 负责人 | - | storage-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"DataClassification": "Confidential"} |

**AccountKind说明**:
- **StorageV2**: 通用v2，推荐使用，支持所有服务
- **BlobStorage**: 仅Blob存储
- **FileStorage**: 仅文件存储（需Premium层）

**ReplicationType说明**:
- **LRS**: 本地冗余存储
- **ZRS**: 区域冗余存储
- **GRS**: 异地冗余存储
- **RAGRS**: 读取访问异地冗余存储
- **GZRS**: 异地区域冗余存储
- **RAGZRS**: 读取访问异地区域冗余存储

**NetworkRules JSON示例**:
```json
{
  "defaultAction": "Deny",
  "bypass": ["AzureServices"],
  "ipRules": [
    {
      "value": "203.0.113.0/24",
      "action": "Allow"
    }
  ],
  "virtualNetworkRules": [
    {
      "vnetReference": "vnet-main",
      "subnetReference": "subnet-app",
      "action": "Allow"
    }
  ]
}
```

**BlobContainers JSON示例**:
```json
[
  {
    "name": "app-data",
    "publicAccess": "None",
    "metadata": {
      "department": "engineering"
    }
  },
  {
    "name": "backups",
    "publicAccess": "None"
  }
]
```

---

### Azure_SQL

**用途**: 定义Azure SQL数据库和服务器

| 列名 | 类型 | 必填 | 说明 | 验证规则 | 示例值 |
|------|------|------|------|----------|--------|
| ResourceName | 文本 | [必填] | 数据库名称 | 字母数字-_ | sqldb-ecommerce-prod |
| Environment | 下拉 | [必填] | 环境 | 见通用说明 | Production |
| Project | 文本 | [必填] | 项目名称 | - | ecommerce-platform |
| ResourceGroup | 文本 | [必填] | 资源组名称 | - | rg-ecommerce-prod |
| Location | 下拉 | [必填] | Azure区域 | 见Azure区域列表 | eastus |
| ServerName | 文本 | [必填] | SQL服务器名称 | 小写字母数字-，全局唯一 | sqlsvr-ecommerce-prod |
| ServerAdminLogin | 文本 | [必填] | 服务器管理员账户 | 字母开头，字母数字_ | sqladmin |
| ServerAdminPassword | 文本 | [必填] | 服务器管理员密码 | 8-128字符，包含大小写数字特殊字符 | 请使用强密码 |
| SQLVersion | 下拉 | [必填] | SQL Server版本 | 12.0 (SQL Server 2014及以上) | 12.0 |
| DatabaseEdition | 下拉 | [必填] | 数据库版本 | Basic/Standard/Premium/GeneralPurpose/BusinessCritical/Hyperscale | GeneralPurpose |
| ServiceObjective | 下拉 | [必填] | 服务目标(SKU) | 依赖Edition | GP_Gen5_2 |
| MaxSizeGB | 数字 | [必填] | 最大存储(GB) | 依赖Edition，1-4096 | 250 |
| Collation | 文本 | [可选] | 排序规则 | 默认SQL_Latin1_General_CP1_CI_AS | SQL_Latin1_General_CP1_CI_AS |
| ZoneRedundant | 下拉 | [可选] | 区域冗余 | true/false，默认false | true |
| ReadScaleOut | 下拉 | [可选] | 读取横向扩展 | Enabled/Disabled，默认Disabled | Enabled |
| PublicNetworkAccess | 下拉 | [必填] | 公网访问 | Enabled/Disabled | Disabled |
| MinimalTLSVersion | 下拉 | [必填] | 最小TLS版本 | 1.0/1.1/1.2 | 1.2 |
| VNet_Reference | 引用 | [可选] | 虚拟网络引用 | 用于VNet集成 | vnet-main |
| Subnet_Reference | 引用 | [可选] | 子网引用 | 需要委派给Microsoft.Sql | subnet-db |
| FirewallRules | JSON | [可选] | 防火墙规则 | 见JSON Schema | 见下方示例 |
| VirtualNetworkRules | JSON | [可选] | 虚拟网络规则 | 见JSON Schema | 见下方示例 |
| TransparentDataEncryption | 下拉 | [必填] | 透明数据加密 | Enabled/Disabled | Enabled |
| BackupRetentionDays | 数字 | [必填] | 短期备份保留天数 | 7-35 | 14 |
| LongTermRetention | JSON | [可选] | 长期备份保留策略 | 见JSON Schema | 见下方示例 |
| ThreatDetection | 下拉 | [可选] | 威胁检测 | Enabled/Disabled，默认Disabled | Enabled |
| AuditingEnabled | 下拉 | [可选] | 审计 | true/false，默认false | true |
| Owner | 文本 | [可选] | 负责人 | - | dba-team@accenture.com |
| CostCenter | 文本 | [可选] | 成本中心 | - | CC-12345 |
| Tags | JSON | [可选] | 额外标签 | 有效JSON | {"Criticality": "High"} |

**DatabaseEdition与ServiceObjective对应关系**:

**Basic**:
- Basic

**Standard**:
- S0, S1, S2, S3, S4, S6, S7, S9, S12

**Premium**:
- P1, P2, P4, P6, P11, P15

**GeneralPurpose** (vCore模型):
- GP_Gen5_2, GP_Gen5_4, GP_Gen5_8, GP_Gen5_16, GP_Gen5_32, GP_Gen5_80

**BusinessCritical** (vCore模型):
- BC_Gen5_2, BC_Gen5_4, BC_Gen5_8, BC_Gen5_16, BC_Gen5_32, BC_Gen5_80

**Hyperscale** (vCore模型):
- HS_Gen5_2, HS_Gen5_4, HS_Gen5_8, HS_Gen5_16, HS_Gen5_32, HS_Gen5_80

**FirewallRules JSON示例**:
```json
[
  {
    "name": "AllowOfficeIP",
    "startIpAddress": "203.0.113.10",
    "endIpAddress": "203.0.113.20"
  },
  {
    "name": "AllowAzureServices",
    "startIpAddress": "0.0.0.0",
    "endIpAddress": "0.0.0.0"
  }
]
```

**VirtualNetworkRules JSON示例**:
```json
[
  {
    "name": "AllowAppSubnet",
    "vnetReference": "vnet-main",
    "subnetReference": "subnet-app",
    "ignoreMissingVnetServiceEndpoint": false
  }
]
```

**LongTermRetention JSON示例**:
```json
{
  "weeklyRetention": "P4W",
  "monthlyRetention": "P12M",
  "yearlyRetention": "P5Y",
  "weekOfYear": 1
}
```

**注意事项**:
1. **服务器名称全局唯一**: `{servername}.database.windows.net` 必须全局唯一
2. **密码复杂度要求**: 必须包含大写、小写、数字和特殊字符中的至少三种
3. **VNet集成**: 如果使用VNet规则，子网必须启用 `Microsoft.Sql` 服务终结点
4. **公网访问**: 生产环境强烈建议设置为 Disabled
5. **备份策略**: 
   - 短期备份自动进行（7-35天）
   - 长期备份需要额外配置
6. **区域冗余**: 仅在 Premium、BusinessCritical 和 Hyperscale 版本中可用

---

## 数据验证规则

### 1. CIDR格式验证
```regex
^([0-9]{1,3}\.){3}[0-9]{1,3}\/([0-9]|[1-2][0-9]|3[0-2])$
```

### 2. IP地址验证
```regex
^([0-9]{1,3}\.){3}[0-9]{1,3}$
```

### 3. JSON格式验证
- 必须是有效的JSON字符串
- 建议使用在线JSON验证工具检查

### 4. 资源引用验证
- 引用的资源名称必须存在于对应的Sheet中
- 引用的资源必须在同一云平台（AWS或Azure）
- 对于跨Sheet引用，系统将自动检查依赖关系

### 5. 全局唯一名称验证
- AWS S3存储桶名称
- Azure存储账户名称
- Azure SQL服务器名称

### 6. 命名规范验证
- AWS资源: 字母、数字、连字符(-)、下划线(_)
- Azure资源: 根据资源类型有不同要求（详见各资源说明）

---

## JSON格式字段Schema

### SecurityGroup IngressRules/EgressRules Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["protocol", "from_port", "to_port"],
    "properties": {
      "protocol": {
        "type": "string",
        "enum": ["tcp", "udp", "icmp", "-1"]
      },
      "from_port": {
        "type": "integer",
        "minimum": 0,
        "maximum": 65535
      },
      "to_port": {
        "type": "integer",
        "minimum": 0,
        "maximum": 65535
      },
      "cidr_blocks": {
        "type": "array",
        "items": {"type": "string"}
      },
      "source_security_group_id": {"type": "string"},
      "description": {"type": "string"}
    }
  }
}
```

### Tags Schema (通用)
```json
{
  "type": "object",
  "patternProperties": {
    "^[a-zA-Z0-9-_]+$": {
      "type": "string"
    }
  }
}
```

### S3 LifecycleRules Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "status"],
    "properties": {
      "id": {"type": "string"},
      "status": {
        "type": "string",
        "enum": ["Enabled", "Disabled"]
      },
      "transitions": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "days": {"type": "integer", "minimum": 0},
            "storage_class": {
              "type": "string",
              "enum": ["STANDARD_IA", "INTELLIGENT_TIERING", "GLACIER", "DEEP_ARCHIVE"]
            }
          }
        }
      },
      "expiration": {
        "type": "object",
        "properties": {
          "days": {"type": "integer", "minimum": 1}
        }
      }
    }
  }
}
```

### Azure NSG SecurityRules Schema
```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["name", "priority", "direction", "access", "protocol"],
    "properties": {
      "name": {"type": "string"},
      "priority": {
        "type": "integer",
        "minimum": 100,
        "maximum": 4096
      },
      "direction": {
        "type": "string",
        "enum": ["Inbound", "Outbound"]
      },
      "access": {
        "type": "string",
        "enum": ["Allow", "Deny"]
      },
      "protocol": {
        "type": "string",
        "enum": ["Tcp", "Udp", "Icmp", "*"]
      },
      "sourcePortRange": {"type": "string"},
      "destinationPortRange": {"type": "string"},
      "sourceAddressPrefix": {"type": "string"},
      "destinationAddressPrefix": {"type": "string"},
      "description": {"type": "string"}
    }
  }
}
```

---

## 使用示例

### 完整AWS资源创建示例

**Scenario**: 创建一个包含Web服务器的基础架构

1. **AWS_VPC Sheet**:
   - ResourceName: `web-vpc`
   - CIDR_Block: `10.0.0.0/16`

2. **AWS_Subnet Sheet** (2行):
   - 行1: `public-subnet` - `10.0.1.0/24` - SubnetType: Public
   - 行2: `private-subnet` - `10.0.2.0/24` - SubnetType: Private

3. **AWS_SecurityGroup Sheet** (2行):
   - 行1: `web-sg` - 允许443端口
   - 行2: `ssh-sg` - 仅允许内网SSH

4. **AWS_EC2 Sheet**:
   - VPC_Reference: `web-vpc`
   - Subnet_Reference: `public-subnet`
   - SecurityGroups: `web-sg,ssh-sg`

5. **AWS_S3 Sheet**:
   - 用于存储静态资源

### 完整Azure资源创建示例

**Scenario**: 创建一个数据库后端服务

1. **Azure_VNet Sheet**:
   - ResourceName: `vnet-backend`
   - AddressSpace: `10.1.0.0/16`

2. **Azure_Subnet Sheet** (2行):
   - 行1: `subnet-app` - `10.1.1.0/24`
   - 行2: `subnet-db` - `10.1.2.0/24` - ServiceEndpoints: Microsoft.Sql

3. **Azure_NSG Sheet**:
   - ResourceName: `nsg-db`
   - 仅允许来自app subnet的1433端口

4. **Azure_SQL Sheet**:
   - VNet_Reference: `vnet-backend`
   - Subnet_Reference: `subnet-db`
   - PublicNetworkAccess: Disabled

---

## 常见错误和解决方案

### 错误1: 无效的CIDR格式
**错误示例**: `10.0.0.0/33`
**正确示例**: `10.0.0.0/16`
**说明**: 子网掩码必须在0-32之间

### 错误2: 子网CIDR超出VPC范围
**错误**: Subnet CIDR `192.168.0.0/24` 不在 VPC `10.0.0.0/16` 范围内
**解决**: 确保子网地址在VPC地址空间内

### 错误3: 资源引用不存在
**错误**: EC2引用的VPC `main-vpc` 在AWS_VPC Sheet中不存在
**解决**: 检查ResourceName拼写，确保被引用资源已定义

### 错误4: JSON格式错误
**错误示例**: `{port: 443}` (缺少引号)
**正确示例**: `{"port": 443}`
**工具**: 使用 jsonlint.com 验证