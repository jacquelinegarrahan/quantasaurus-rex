#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { QuantasaurusStack } from './stacks/quantasaurus-stack';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '../.env' });

const app = new cdk.App();

// Get environment settings
const environment = process.env.ENVIRONMENT || 'development';
const awsAccountId = process.env.AWS_ACCOUNT_ID || process.env.CDK_DEFAULT_ACCOUNT;
const awsRegion = process.env.AWS_REGION || process.env.CDK_DEFAULT_REGION || 'us-east-1';

// Create the stack
new QuantasaurusStack(app, `QuantasaurusStack-${environment}`, {
  env: {
    account: awsAccountId,
    region: awsRegion,
  },
  
  // Stack properties
  stackName: `quantasaurus-rex-${environment}`,
  description: 'Quantasaurus Rex - AI-powered portfolio analysis system',
  
  // Custom properties
  environment: environment,
  
  // Tags
  tags: {
    Project: 'QuantasaurusRex',
    Environment: environment,
    ManagedBy: 'CDK',
    Owner: 'JacquelineGarrahan'
  }
});

// Add stack-level tags
cdk.Tags.of(app).add('Project', 'QuantasaurusRex');
cdk.Tags.of(app).add('ManagedBy', 'CDK');