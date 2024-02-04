import orjson as json

from django.db import transaction

from project_apps.repository.workflow_repository import WorkflowRepository
from project_apps.repository.job_repository import JobRepository
from project_apps.repository.history_repository import HistoryRepository
from project_apps.api.serializers import serialize_workflow
from project_apps.models.cache import Cache
from project_apps.engine.job_dependency import job_dependency


class WorkflowService:
    def __init__(self):
        self.workflow_repository = WorkflowRepository()
        self.job_repository = JobRepository()

    def create_workflow(self, name, description, jobs_data):
        workflow = self.workflow_repository.create_workflow(
            name=name, 
            description=description
        )

        # 의존성 카운트 계산
        depends_count = {job_data['name']: 0 for job_data in jobs_data}
        for job_data in jobs_data:
            for next_job_name in job_data.get('next_job_names', []):
                if next_job_name in depends_count:
                    depends_count[next_job_name] += 1

        # 작업 정보 생성 및 추가
        jobs_info = []
        for job_data in jobs_data:
            job = self.job_repository.create_job(
                workflow_uuid=workflow.uuid,
                name=job_data['name'],
                image=job_data['image'],
                parameters=job_data.get('parameters', {}),
                next_job_names=job_data.get('next_job_names', []),
                depends_count=depends_count[job_data['name']]
            )

            jobs_info.append({
            'uuid': job.uuid,
            'name': job.name,
            'image': job.image,
            'parameters': job.parameters,
            'depends_count': job.depends_count,
            'next_job_names': job.next_job_names
            })
        
        # 워크플로우 정보 생성
        workflow_info = {
            'uuid': workflow.uuid,
            'name': workflow.name,
            'description': workflow.description
        }
        
        # 워크플로우와 작업 목록을 함께 직렬화
        serialized_workflow = serialize_workflow(workflow_info, jobs_info)

        return serialized_workflow

    @transaction.atomic
    def delete_workflow(self, workflow_uuid):
        workflow = self.workflow_repository.get_workflow(workflow_uuid)
        jobs = self.job_repository.get_job_list(workflow_uuid)

        # Workflow 삭제
        self.workflow_repository.delete_workflow(workflow.uuid)

        # Jobs 삭제
        for job in jobs:
            self.job_repository.delete_job(job.uuid)


class WorkflowExecutor:
    def __init__(self):
        self.job_repository = JobRepository()
        self.history_repository = HistoryRepository()
        self.cache = Cache()

    def execute_workflow(self, workflow_uuid):
        job_list = self.job_repository.get_job_list(workflow_uuid)
        for job in job_list:
            job['result'] = 'waiting'

        if job_list:
            job_list_json = json.dumps(job_list)
            self.cache.set(workflow_uuid, job_list_json)
            history = self.history_repository.create_history(workflow_uuid)
            job_dependency.apply_async(args=[workflow_uuid, history.uuid])

            return True
        else:
            return False