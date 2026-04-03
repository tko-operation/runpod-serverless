import runpod

def handler(event):
    return {
        "ok": True,
        "message": "hello world"
    }

runpod.serverless.start({"handler": handler})
