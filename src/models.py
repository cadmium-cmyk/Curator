import uuid
from dataclasses import dataclass, field
from typing import Optional
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject, Gio

@dataclass
class ProjectMetadata:
    portfolio_title: str = "Portfolio"
    artist_name: str = "Artist Name"
    role: str = "Concept Artist"
    email: str = ""
    bio: str = ""
    social_link: str = ""
    cv_link: str = ""
    
    def to_dict(self): return self.__dict__
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class PortfolioAsset:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = "Untitled"
    source_path: str = ""
    thumbnail_path: Optional[str] = None
    description: str = ""
    medium: str = ""
    year: str = ""
    link: str = ""
    notes: str = "" 
    tags: list[str] = field(default_factory=list)
    def to_dict(self): return {k: v for k, v in self.__dict__.items()}
    @classmethod
    def from_dict(cls, data): return cls(**data)

class AssetObject(GObject.Object):
    __gtype_name__ = 'AssetObject'
    def __init__(self, asset: PortfolioAsset, **kwargs):
        super().__init__(**kwargs)
        self._asset = asset
    @GObject.Property(type=str)
    def title(self): return self._asset.title
    @title.setter
    def title(self, v): self._asset.title = v; self.notify("title")
    @GObject.Property(type=str)
    def source_path(self): return self._asset.source_path
    @GObject.Property(type=str)
    def description(self): return self._asset.description
    @description.setter
    def description(self, v): self._asset.description = v; self.notify("description")
    @GObject.Property(type=str)
    def thumbnail_path(self): return self._asset.thumbnail_path or ""
    @GObject.Property(type=str)
    def medium(self): return self._asset.medium
    @medium.setter
    def medium(self, v): self._asset.medium = v; self.notify("medium")
    @GObject.Property(type=str)
    def year(self): return self._asset.year
    @year.setter
    def year(self, v): self._asset.year = v; self.notify("year")
    @GObject.Property(type=str)
    def link(self): return self._asset.link
    @link.setter
    def link(self, v): self._asset.link = v; self.notify("link")
    @GObject.Property(type=str)
    def notes(self): return self._asset.notes
    @notes.setter
    def notes(self, v): self._asset.notes = v; self.notify("notes")
    @GObject.Property(type=str)
    def tags_string(self): return ", ".join(self._asset.tags)
    @tags_string.setter
    def tags_string(self, v): 
        self._asset.tags = [t.strip() for t in v.split(",") if t.strip()]
        self.notify("tags-string")
    def get_asset(self): return self._asset

class ProjectModel:
    def __init__(self): 
        self.store = Gio.ListStore(item_type=AssetObject)
        self.metadata = ProjectMetadata() # Holds project settings

    def add_asset(self, asset: PortfolioAsset): self.store.append(AssetObject(asset))
    def insert_asset_object(self, index, obj):
        if index < 0: index = 0
        if index > self.store.get_n_items(): index = self.store.get_n_items()
        self.store.insert(index, obj)
    def remove_asset_object(self, obj):
        for i in range(self.store.get_n_items()):
            if self.store.get_item(i) == obj: self.store.remove(i); break
    def get_all_assets(self): return [self.store.get_item(i).get_asset() for i in range(self.store.get_n_items())]
    def clear(self): 
        self.store.remove_all()
        self.metadata = ProjectMetadata() # Reset meta

    def reorder_asset(self, old_index, new_index):
        if old_index == new_index: return
        item = self.store.get_item(old_index)
        self.store.remove(old_index)
        if old_index < new_index: new_index -= 1
        new_index = max(0, min(new_index, self.store.get_n_items()))
        self.store.insert(new_index, item)
