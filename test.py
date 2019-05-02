class A:
    st = {}

    def __new__(cls, iid):
        print(iid)
        if iid in cls.st:
            return cls.st[iid]
        else:
            new = super().__new__(cls)
            cls.st[iid] = new
            return new

    def __init__(self, iid):
        print(iid)
        self.id = iid
