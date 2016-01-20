#
# THIS CODE AND INFORMATION ARE PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS
# FOR A PARTICULAR PURPOSE. THIS CODE AND INFORMATION ARE NOT SUPPORTED BY XEBIALABS.
#
import smtplib
import datetime, time

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.MIMEBase import MIMEBase
from email import Encoders


from xldeploy.XLDeployClientUtil import XLDeployClientUtil

def send_email(message, subject, succes=True, attachement=None):

    sender = mailServer['senderAddress']

    if succes:
        receivers = notifyOnSuccess
    else:
        receivers = notifyOnFailure


    msg = MIMEMultipart('alternative')
    msg.attach(MIMEText(message, 'html'))
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receivers

    if attachement:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(attachement)
        Encoders.encode_base64(part)

        part.add_header('Content-Disposition', 'attachment; filename="xldeployTaskOverview.txt"')

        msg.attach(part)


    smtpObj = smtplib.SMTP(mailServer['smtpHost'], mailServer['smtpPort'])
    smtpObj.starttls()
    smtpObj.login(mailServer['username'], mailServer['password'])
    smtpObj.sendmail(sender, receivers, msg.as_string())
    smtpObj.quit()
    print "Successfully notified users via email"
    return True

def send_success_mail(deploymentPackage, environment):
    ts = datetime.datetime.fromtimestamp(timestamp()).strftime('%Y-%m-%d %H:%M:%S')
    subject = "XL-Release: Succesfull deployment of %s onto %s happend at %s" % (deploymentPackage, environment, ts )
    message = """
      <html>
        <head></head>
            <body>
                <p>Succesfull deployment of %s onto %s at %s <br>
                </p>
            </body>
        </html>
    """ % (deploymentPackage, environment, ts )
    send_email(message, subject)

def send_failure_mail(deploymentPackage, environment, taskId = None):
    ts = datetime.datetime.fromtimestamp(timestamp()).strftime('%Y-%m-%d %H:%M:%S')
    subject = "XL-Release: Deployment of %s onto %s FAILED at %s" % (deploymentPackage, environment, ts )
    message = """
      <html>
        <head></head>
            <body>
                <p>Deployment of <b>%s</b> onto <b>%s</b> FAILED at <b>%s</b> <br>
                But here is a nice pink pony to cheer u up
                </p>
            </body>
        </html>
    """ % (deploymentPackage, environment, ts )

    attachmentText = None

    if taskId:
        attachmentText = xldClient.getTaskInfo(taskId)

    send_email(message, subject, False, attachmentText)


def timestamp():
    return time.time()

xldClient = XLDeployClientUtil.createXLDeployClient(xldeployServer, username, password)

deployment = None
if xldClient.deploymentExists(deploymentPackage, environment):
    print "Upgrading deployment \n"
    deployment = xldClient.deploymentPrepareUpdate(deploymentPackage,environment)
else:
    print "Creating initial deploy \n"
    deployment = xldClient.deploymentPrepareInitial(deploymentPackage, environment)

# Mapping deployables to the target environment
print "Mapping all deployables \n"
deployment = xldClient.deployment_prepare_deployeds(deployment, orchestrators, deployedApplicationProperties, deployedProperties)

# deploymentProperties + configure orchestrators
# print "DEBUG: Deployment description is now: %s" % deployment
# Validating the deployment
print "Creating a deployment task \n"
taskId = xldClient.get_deployment_task_id(deployment)

print "Execute task with id: %s" % taskId
taskState = xldClient.invoke_task_and_wait_for_result(taskId, pollingInterval, numberOfPollingTrials, continueIfStepFails, numberOfContinueRetrials)

if taskState in ('DONE','EXECUTED'):
    print "Deployment ended in %s \n" % taskState
    xldClient.archiveTask(taskId)
    send_success_mail(deploymentPackage, environment)
    sys.exit(0)

# rollbackOnError
if rollbackOnError and taskState in ('FAILED', 'STOPPED'):
    print "Going to rollback \n"
    xldClient.stopTask(taskId)
    rollBackTaskId = xldClient.deploymentRollback(taskId)
    taskState = xldClient.invoke_task_and_wait_for_result(rollBackTaskId, pollingInterval, numberOfPollingTrials, continueIfStepFails, numberOfContinueRetrials)
    xldClient.archiveTask(rollBackTaskId)
    send_failure_mail(deploymentPackage, environment,taskId)
    sys.exit(1)
elif taskState in ('FAILED', 'STOPPED'):
    print "Task failed, rollback not enabled. \n"
    xldClient.cancelTask(taskId)
    send_failure_mail(deploymentPackage, environment, taskId)
    sys.exit(1)
