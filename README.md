# aws-unused-workspace-scan

如何使用Lambda定时巡检闲置
Workspace实例Demo
背景
当前Workspace console不具备批量计算实例被闲置时间的功能，这导致IT管理员无法做到细致的成本管理，尤其是在大量使用ALWAYS ON的实例的情况下。本文将会介绍一个简单的用量巡检工具帮助用户找出闲置的Workspace，以实现更好的成本管理。
解决方案
本解决方案使用了Python编写了一套程序，这套程序部署在Lambda上，并由EventBrige以一定时间为周期的定时触发。程序首先会使用Workspace API查询出实例的基本信息，根据这些信息计算出空闲时间IdleTime后，生成csv文件存储在S3服务的桶中便于用户进行查阅，并且过SNS服务将一个简单的报告发送给用户所指定的邮箱。下列为csv报告的示例：

WorkspaceId,UserName,IdleTime
ws-wffzz17c1,jhuang,14d5h2m      #此实例已空闲14d5h2m
ws-66zxzp4vb,jhuang5,n/a。         #此实例从未被使用过，IdleTime无法计算

整体架构 

![image](https://github.com/AutoJunjie/aws-unused-workspace-scan/assets/38706868/db621ca8-18eb-4958-a9c5-102df31e8c71)

部署过程
1.	创建S3 Bucket
o	进入s3 console，Bucket name填入workspace-usage-report-demo-bucket保留其他的默认配置，点击Create
 
o	创建后查看bucket的详情，记录下Amazon Resource Name (ARN)，此信息需要在第3步中配置Lambda role赋予IAM权限的时候使用
 
2.	创建SNS Topic并用订阅
o	进入SNS console，type选择Standard，Name填入workspace-usage-report-demo，点击Create Topic
 
o	创建后查看topic的详情，记录下ARN，此信息需要在第3步中配置Lambda role赋予IAM权限的时候使用，记录完后点击Create subscription  
o	进入Create subscription 后，ARN选中上一步创建出来的topic ARN，Protocol选择Email，在endpoint中输入你希望收到邮件的邮箱地址，点击Create subscription后你所输入的邮件将会收到一封邮件确认你的topic订阅。
 
o	收到邮件后点击Confirm subscription，订阅成功
 
 


3.	创建Lambda Function，并为Lambda的IAM role赋予所需权限
o	将Function命名为workspace_usage_report_demo，Runtime选择Python3.9，其中Excution role选择默认的create a new role with basic lambda permission，Advanced settings的选项都留空即可
 
o	选择Code 选项卡，将下列python代码覆盖到AWS自动生成lambda_function.py的原有代码上，点击Deploy部署代码
 
o	选择Configuration选项卡，点击General configuration，点击edit，Timeout部分改为10秒，点击save
 
o	返回Configuration选项卡，点击Environment Variables，点击edit，然后点击Add environment variable:
	添加Key：s3_bucket_name, Value为第1步创建S3 bucket的名字
	添加Key：sns_topic_arn, Value为第2步创建的SNS 的topic ARN
	点击Save
 
o	选择Permission选项卡，点击Role name跳转到IAM console
 
o	点击Add permission，在下拉框下选择Create inline policy
 
o	点击JSON 选项卡并粘贴下IAM policy的JSON，点击review policy，注意其中SNS以及S3的Resource需替换为您环境中的在第1，2步里创建的SNS Topic ARN以及S3 ARN， workspace的resource可保留为 *
     IAM policy JSON
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "workspaces:*",
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "sns:*",
            "Resource": "arn:aws-cn:sns:cn-northwest-1:145525377082:workspace_usage_report_demo"
        },
        {
            "Sid": "VisualEditor2",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": [
                "arn:aws-cn:s3:::workspace-usage-report-demo-bucket/*",
                "arn:aws-cn:s3:::workspace-usage-report-demo-bucket"
            ]
        }
    ]
}
 

o	给policy命名workspace_usage_report_demo_policy，并点击create policy
 
o	给回到lambda console 的code选项卡，点解test创建test event，选择hello-world模版，event name填入test，点击创建
 
o	再次点击test让Lambda运行代码进行测试（3s～10s），若成功你会得到与下图相似的结果
 
o	运行成功后你将会收到一封邮件通知
 
o	并且你可以通过AWS CLI下载到你本地，并查看存放在S3bucket中的报告
 




4.	在Amazon EventBridge创建Rule，定时触发Lambda执行任务
o	登陆Amazon EventBridge console并点击create rule，Name输入workspace-usage-report-demo，rule type选择schedule，点击Next
 
o	填入你所需要的触发频率，在这个demo里我选择了在每个月的第一天的早上8点执行任务，点击Next。注意问号不要写入中文的问好，更详细的配置指导与例子请参考：https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html
 
o	Target Type选择 Lambda，指定我们在之前创建好的lambda function，Step3和4直接Next不需要做修改
 

o	检查无误后点解Create rule
 
o	回到lambda function console中，event bridege已绑定Lambda
 

参考链接

•	AWS CLI 用户指南： https://docs.aws.amazon.com/zh_cn/cli/latest/userguide/getting-started-prereqs.html

•	适用于 Python 的 AWS 开发工具包 (Boto3)： 
https://aws.amazon.com/cn/sdk-for-python/?nc1=h_ls

•	Workspace python模块使用指南：
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/workspaces.html

•	Workspace API参考：
https://docs.aws.amazon.com/zh_cn/workspaces/latest/api/welcome.html
