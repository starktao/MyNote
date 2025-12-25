class R:
    @staticmethod
    def success(data=None, msg="success", code=0):
        return {"code": int(code), "msg": msg, "data": data}

    @staticmethod
    def error(msg="error", code=500, data=None):
        return {"code": int(code), "msg": msg, "data": data}

