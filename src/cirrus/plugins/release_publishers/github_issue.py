from utilitarian import credentials, github, servicenow

from release_publishers.base import ReleaseInfoExtractor


class GitHubIssueReleaseInfoExtractor(ReleaseInfoExtractor):
    """
    ReleaseInfoExtractor that extracts info from GitHub issues
    """
    _plugin = 'github_issue'

    def get_service_now_params(self, id_, params=None):
        sn_params = servicenow.TicketArgs()
        if params is not None:
            sn_params.from_dict(params)
        # TODO figure out a cleaner way to get creds...this seems strange
        gh_auth_user, gh_auth_pass = self.config.get_gethub_auth()
        creds = credentials.Config(
            inline_cfg={
                'github': {  # where's this come from (here maybe: https://github.ibm.com/cloudant/utilitarian/blob/master/utilitarian/config_specs/cloudant.json)? example from carb (environment_request_database uses 'github_enterprise')
                    'url': 'https://github.com',
                    'username': gh_auth_user,
                    'token': gh_auth_pass
                }
            }
        )
        gh_issue = ReleaseIssue.load(
            self.config.organisation_name(),
            self.config.package_name(),
            id_,
            creds=creds
        )
        sn_params.user = gh_issue.opened_by
        sn_params.impact = 'CHANGEME'
        sn_params.purpose = gh_issue.purpose_and_stakeholders
        sn_params.description = gh_issue.short_description
        sn_params.backup_plan = 'CHANGEME'
        sn_params.type = 'standard'
        sn_params.prod_ready = True
        sn_params.env = gh_issue.environments

        return sn_params


class ReleaseIssue(github.GitHubIssue):
    """
    Extends GitHubIssue to add properties based on template

    ..todo:: move this to https://github.ibm.com/cloudant/cloudant-common
    """
    def __init__(self):
        super()
        # TODO: maybe change this schema so it directly maps to SN fields
        self.schema.update({
            "environments": {'_type': 'list', 'required': True},
            "short_description": {'_type': 'str', 'required': True},
            "purpose_and_stakeholders": {'_type': 'str', 'required': True},
            "readiness": {'_type': 'str', 'required': True},
            "communication_plan": {'_type': 'str', 'required': True},
            "deployment_steps": {'_type': 'str', 'required': True},
        })

#     @property
#     def environments(self):
#         raise NotImplementedError
# 
#     @property
#     def short_description(self):
#         raise NotImplementedError
# 
#     @property
#     def purpose(self):
#         raise NotImplementedError
# 
#     @property
#     def readiness(self):
#         raise NotImplementedError
# 
#     @property
#     def communications(self):
#         raise NotImplementedError
# 
#     @property
#     def deployment(self):
#         raise NotImplementedError
