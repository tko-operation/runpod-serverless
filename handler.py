import runpod

def handler(job):
    return {"ok": True, "message": "hello world"}

runpod.serverless.start({"handler": handler})
