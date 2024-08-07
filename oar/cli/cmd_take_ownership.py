import click
import logging
import re
import oar.core.util as util
from oar.core.worksheet_mgr import WorksheetManager, WorksheetException
from oar.core.jira_mgr import JiraManager, JiraException
from oar.core.advisory_mgr import AdvisoryManager, AdvisoryException
from oar.core.config_store import ConfigStore
from oar.core.notification_mgr import NotificationManager, NotificationException
from oar.core.const import *

logger = logging.getLogger(__name__)


def validate_email(ctx, param, value):
    email_pattern = re.compile(
        r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    if not email_pattern.match(value):
        raise click.BadParameter(f"{value} is not a valid email")
    return value


@click.command()
@click.option(
    "-e",
    "--email",
    required=True,
    callback=validate_email,
    help="email address of the owner",
)
@click.pass_context
def take_ownership(ctx, email):
    """
    Take ownership for advisory and jira subtasks
    """
    # get config store from context
    cs = ctx.obj["cs"]
    cs.set_owner(email)

    try:
        # get existing report
        wm = WorksheetManager(cs)
        report = wm.get_test_report()
        # update task status to in progress
        report.update_task_status(LABEL_TASK_OWNERSHIP, TASK_STATUS_INPROGRESS)
        # update assignee of QE subtasks and change status of test verification ticket to in_progress
        updated_subtasks = JiraManager(cs).change_assignee_of_qe_subtasks()
        # update owner of advisories which status is QE
        updated_ads, abnormal_ads = AdvisoryManager(cs).change_ad_owners()
        # send notification
        NotificationManager(cs).share_ownership_change_result(
            updated_ads, abnormal_ads, updated_subtasks, cs.get_owner()
        )
        # update task status to pass
        report.update_task_status(LABEL_TASK_OWNERSHIP, TASK_STATUS_PASS)
    except Exception as e:
        logger.exception("take ownership of advisory and jira subtasks failed")
        report.update_task_status(LABEL_TASK_OWNERSHIP, TASK_STATUS_FAIL)
        raise
