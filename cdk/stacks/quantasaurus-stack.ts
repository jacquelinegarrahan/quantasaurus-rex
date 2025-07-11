import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as ssm from 'aws-cdk-lib/aws-ssm';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as path from 'path';

export interface QuantasaurusStackProps extends cdk.StackProps {
  environment: string;
}

export class QuantasaurusStack extends cdk.Stack {
  public readonly lambdaFunction: lambda.Function;
  public readonly eventRule: events.Rule;
  public readonly deadLetterQueue: sqs.Queue;
  public readonly alarmsSnsTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: QuantasaurusStackProps) {
    super(scope, id, props);

    // Create Dead Letter Queue for failed executions
    this.deadLetterQueue = new sqs.Queue(this, 'DeadLetterQueue', {
      queueName: `quantasaurus-rex-dlq-${props.environment}`,
      retentionPeriod: cdk.Duration.days(14),
      visibilityTimeout: cdk.Duration.minutes(5)
    });

    // Create SNS topic for alarms
    this.alarmsSnsTopic = new sns.Topic(this, 'AlarmsTopic', {
      topicName: `quantasaurus-rex-alarms-${props.environment}`,
      displayName: 'Quantasaurus Rex Alarms'
    });

    // Add email subscription for alarms
    if (process.env.EMAIL_RECIPIENT) {
      this.alarmsSnsTopic.addSubscription(
        new subscriptions.EmailSubscription(process.env.EMAIL_RECIPIENT)
      );
    }

    // Create Lambda execution role
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Execution role for Quantasaurus Rex Lambda function',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')
      ]
    });

    // Add SES permissions
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'ses:SendEmail',
        'ses:SendRawEmail',
        'ses:GetSendQuota',
        'ses:GetSendStatistics'
      ],
      resources: ['*']
    }));

    // Add Systems Manager permissions for device ID storage
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'ssm:GetParameter',
        'ssm:PutParameter',
        'ssm:DeleteParameter',
        'ssm:GetParameters'
      ],
      resources: [
        `arn:aws:ssm:${this.region}:${this.account}:parameter/quantasaurus-rex/*`
      ]
    }));

    // Add CloudWatch permissions for custom metrics
    lambdaRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'cloudwatch:PutMetricData'
      ],
      resources: ['*']
    }));

    // Create Lambda function
    this.lambdaFunction = new lambda.Function(this, 'QuantasaurusFunction', {
      functionName: `quantasaurus-rex-${props.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_handler.handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../src')),
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      role: lambdaRole,
      environment: {
        ENVIRONMENT: props.environment,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY || '',
        TAVILY_API_KEY: process.env.TAVILY_API_KEY || '',
        AIERA_API_KEY: process.env.AIERA_API_KEY || '',
        EMAIL_SENDER: process.env.EMAIL_SENDER || '',
        EMAIL_RECIPIENT: process.env.EMAIL_RECIPIENT || '',
        OPENAI_MODEL: process.env.OPENAI_MODEL || 'o3-2025-04-16',
        ROBINHOOD__USERNAME: process.env.ROBINHOOD__USERNAME || '',
        ROBINHOOD__PASSWORD: process.env.ROBINHOOD__PASSWORD || '',
        AWS_REGION: this.region
      },
      deadLetterQueue: this.deadLetterQueue,
      retryAttempts: 2,
      reservedConcurrentExecutions: 1, // Only one execution at a time
      description: 'Quantasaurus Rex - AI-powered portfolio analysis'
    });

    // Create CloudWatch Log Group with retention
    const logGroup = new logs.LogGroup(this, 'LambdaLogGroup', {
      logGroupName: `/aws/lambda/${this.lambdaFunction.functionName}`,
      retention: logs.RetentionDays.ONE_MONTH,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Create EventBridge rule for daily execution at 9AM ET (1PM UTC)
    this.eventRule = new events.Rule(this, 'DailyExecutionRule', {
      ruleName: `quantasaurus-rex-daily-${props.environment}`,
      description: 'Daily execution of Quantasaurus Rex portfolio analysis at 9AM ET',
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '13', // 9AM ET = 1PM UTC
        day: '*',
        month: '*',
        year: '*'
      }),
      enabled: props.environment === 'production'
    });

    // Add Lambda as target for the rule
    this.eventRule.addTarget(new targets.LambdaFunction(this.lambdaFunction, {
      deadLetterQueue: this.deadLetterQueue,
      maxEventAge: cdk.Duration.hours(2),
      retryAttempts: 2
    }));

    // Create CloudWatch Alarms
    this.createCloudWatchAlarms();

    // Create Systems Manager Parameters
    this.createSSMParameters(props.environment);

    // Output important resources
    new cdk.CfnOutput(this, 'LambdaFunctionArn', {
      value: this.lambdaFunction.functionArn,
      description: 'ARN of the Quantasaurus Rex Lambda function'
    });

    new cdk.CfnOutput(this, 'EventRuleArn', {
      value: this.eventRule.ruleArn,
      description: 'ARN of the EventBridge rule'
    });

    new cdk.CfnOutput(this, 'DeadLetterQueueUrl', {
      value: this.deadLetterQueue.queueUrl,
      description: 'URL of the Dead Letter Queue'
    });

    new cdk.CfnOutput(this, 'AlarmsTopicArn', {
      value: this.alarmsSnsTopic.topicArn,
      description: 'ARN of the SNS topic for alarms'
    });
  }

  private createCloudWatchAlarms(): void {
    // Lambda function errors alarm
    const errorAlarm = new cloudwatch.Alarm(this, 'LambdaErrorAlarm', {
      alarmName: `quantasaurus-rex-errors-${this.node.tryGetContext('environment') || 'dev'}`,
      alarmDescription: 'Alarm for Lambda function errors',
      metric: this.lambdaFunction.metricErrors({
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
    });

    errorAlarm.addAlarmAction(
      new cloudwatch.SnsAction(this.alarmsSnsTopic)
    );

    // Lambda function duration alarm
    const durationAlarm = new cloudwatch.Alarm(this, 'LambdaDurationAlarm', {
      alarmName: `quantasaurus-rex-duration-${this.node.tryGetContext('environment') || 'dev'}`,
      alarmDescription: 'Alarm for Lambda function duration',
      metric: this.lambdaFunction.metricDuration({
        statistic: 'Average',
        period: cdk.Duration.minutes(5)
      }),
      threshold: 600000, // 10 minutes in milliseconds
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
    });

    durationAlarm.addAlarmAction(
      new cloudwatch.SnsAction(this.alarmsSnsTopic)
    );

    // Lambda function throttles alarm
    const throttleAlarm = new cloudwatch.Alarm(this, 'LambdaThrottleAlarm', {
      alarmName: `quantasaurus-rex-throttles-${this.node.tryGetContext('environment') || 'dev'}`,
      alarmDescription: 'Alarm for Lambda function throttles',
      metric: this.lambdaFunction.metricThrottles({
        statistic: 'Sum',
        period: cdk.Duration.minutes(5)
      }),
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
    });

    throttleAlarm.addAlarmAction(
      new cloudwatch.SnsAction(this.alarmsSnsTopic)
    );

    // Dead Letter Queue messages alarm
    const dlqAlarm = new cloudwatch.Alarm(this, 'DeadLetterQueueAlarm', {
      alarmName: `quantasaurus-rex-dlq-messages-${this.node.tryGetContext('environment') || 'dev'}`,
      alarmDescription: 'Alarm for messages in Dead Letter Queue',
      metric: this.deadLetterQueue.metricApproximateNumberOfVisibleMessages({
        statistic: 'Maximum',
        period: cdk.Duration.minutes(5)
      }),
      threshold: 1,
      evaluationPeriods: 1,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
    });

    dlqAlarm.addAlarmAction(
      new cloudwatch.SnsAction(this.alarmsSnsTopic)
    );
  }

  private createSSMParameters(environment: string): void {
    // Create parameter for configuration
    new ssm.StringParameter(this, 'ConfigParameter', {
      parameterName: `/quantasaurus-rex/${environment}/config`,
      stringValue: JSON.stringify({
        version: '1.0.0',
        lastUpdated: new Date().toISOString(),
        environment: environment
      }),
      description: 'Configuration parameters for Quantasaurus Rex'
    });

    // Create parameter for feature flags
    new ssm.StringParameter(this, 'FeatureFlagsParameter', {
      parameterName: `/quantasaurus-rex/${environment}/feature-flags`,
      stringValue: JSON.stringify({
        enableStockAnalysis: true,
        enableCryptoAnalysis: true,
        enableEmailReports: true,
        enableDetailedLogging: environment === 'development'
      }),
      description: 'Feature flags for Quantasaurus Rex'
    });
  }

  // Method to create a custom resource for SES email verification
  private createSESEmailVerification(): void {
    // This would be implemented if automatic email verification is needed
    // For now, emails need to be verified manually in the SES console
  }

  // Method to create custom CloudWatch dashboard
  public createDashboard(): cloudwatch.Dashboard {
    const dashboard = new cloudwatch.Dashboard(this, 'QuantasaurusDashboard', {
      dashboardName: `quantasaurus-rex-${this.node.tryGetContext('environment') || 'dev'}`,
      periodOverride: cloudwatch.PeriodOverride.AUTO
    });

    // Add Lambda metrics widget
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Function Metrics',
        left: [
          this.lambdaFunction.metricInvocations({
            statistic: 'Sum',
            label: 'Invocations'
          }),
          this.lambdaFunction.metricErrors({
            statistic: 'Sum',
            label: 'Errors'
          }),
          this.lambdaFunction.metricThrottles({
            statistic: 'Sum',
            label: 'Throttles'
          })
        ],
        right: [
          this.lambdaFunction.metricDuration({
            statistic: 'Average',
            label: 'Duration (avg)'
          })
        ]
      })
    );

    // Add DLQ metrics widget
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Dead Letter Queue Metrics',
        left: [
          this.deadLetterQueue.metricApproximateNumberOfVisibleMessages({
            statistic: 'Maximum',
            label: 'Visible Messages'
          }),
          this.deadLetterQueue.metricNumberOfMessagesSent({
            statistic: 'Sum',
            label: 'Messages Sent'
          })
        ]
      })
    );

    return dashboard;
  }
}