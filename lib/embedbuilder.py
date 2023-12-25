import json

class Embed():
    def __init__(self, title, description, color):
        self.title = title
        self.description = description
        self.color = color

        self.type = "rich"
        self.fields = []
        self.author = {}
        self.timestamp = None

    def Field(self, name, value, inline=False):
        self.fields.append({
            "name": name,
            "value": value,
            "inline": inline
        })
        return self
    
    def Author(self, name, icon_url=""):
        self.author = {
            "name": name,
            "icon_url": icon_url
        }
        return self

    def Timestamp(self, value):
        self.timestamp = value
        return self

    def Build(self):
        return json.dumps(self.__dict__)
