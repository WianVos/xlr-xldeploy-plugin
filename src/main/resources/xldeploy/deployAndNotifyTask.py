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

def do_email(body, subject, recipients, attachement=None):

    sender = mailServer['senderAddress']


    msg = MIMEMultipart('alternative')
    msg.attach(MIMEText(body, 'html'))
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipients

    if attachement:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(attachement)
        Encoders.encode_base64(part)

        part.add_header('Content-Disposition', 'attachment; filename="xldeployTaskOverview.txt"')

        msg.attach(part)

    try:
        smtpObj = smtplib.SMTP(mailServer['smtpHost'], mailServer['smtpPort'])
        smtpObj.starttls()
        smtpObj.login(mailServer['username'], mailServer['password'])
        smtpObj.sendmail(sender, recipients, msg.as_string())
        smtpObj.quit()
        print "Successfully notified users via email"
        return True
    except Exception as e:
        print "unable to send email to %s" % recipients
        print e.errno
        print e.strerror
        return False

def send_email(taskId = None, success=True, attachDetails=True):
    """
    this function defines the message to be sent to the appropriate list of recipients in case of either failure or success
    :param success: Boolean
    :param attachDetails: Boolean
    :return: True upon successfull send False if not so much ..

    """
    ts = datetime.datetime.fromtimestamp(timestamp()).strftime('%Y-%m-%d %H:%M:%S')
    subject = None
    body = None
    recipients = None

    if success:
        try:
            subject = successNotificationSubject
            body = successNotificationBody
            recipients = notifyOnSuccess
        except ValueError:
            print "not all needed parameters where set on the email task"
    else:
        try:
            subject = failureNotificationSubject
            body = failureNotificationBody
            recipients = notifyOnFailure
        except ValueError:
            print "not all needed parameters where set on the email task"

    body = """
        <html>
            <head></head>
                <body>
                    <p>%s<br>
                    </p>
                </body>
        </html>
    """ % body

    if taskId:
        attachementText =  xldClient.getTaskInfo(taskId)
        if attachDetails:
            return do_email(body, subject, recipients, attachmentText)

    return do_email(body, subject, recipients)


def timestamp():
    return time.time()

try:
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
        send_email(taskId)
        sys.exit(0)
    
    # rollbackOnError
    if rollbackOnError and taskState in ('FAILED', 'STOPPED'):
        print "Going to rollback \n"
        xldClient.stopTask(taskId)
        rollBackTaskId = xldClient.deploymentRollback(taskId)
        taskState = xldClient.invoke_task_and_wait_for_result(rollBackTaskId, pollingInterval, numberOfPollingTrials, continueIfStepFails, numberOfContinueRetrials)
        xldClient.archiveTask(rollBackTaskId)
        send_email(taskId=taskId, success=False)
        sys.exit(1)
    elif taskState in ('FAILED', 'STOPPED'):
        print "Task failed, rollback not enabled. \n"
        xldClient.cancelTask(taskId)
        send_email(taskId=taskId, success=False)
        sys.exit(1)
except Exception:
    send_email(taskId=None, success=False, attachDetails=False)