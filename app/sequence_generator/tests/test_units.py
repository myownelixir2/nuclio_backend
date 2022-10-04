import asyncio
import time
job_st = time.time()

@asyncio.coroutine
def main(job_id, channel_index):

    job = JobRunner(job_id, channel_index)
    res = job.execute()
    processed_job_id = job.result(res)
    
    return processed_job_id

job = JobRunner(test_job_id_cloud, 5)

res = job.execute()

processed_job_id = job.result(res)


job_et = time.time()
job_elapsed_time = job_et - job_st
print('Execution time for "JOB SPECS":', job_elapsed_time, 'seconds')

job_st = time.time()
inputs = [0,1,2,3,4,5]
for i in inputs:
    main(test_job_id_cloud, i)
job_et = time.time()
job_elapsed_time = job_et - job_st
print('Execution time for "JOB SPECS":', job_elapsed_time, 'seconds')