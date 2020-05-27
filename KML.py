'''
Created on 29 juill. 2019

@author: david.larochelle
'''


class KML(object):
    '''
    KML Class is created to handle scanning of multiple image files in multiple folders and ultimately export a KML file compatible
    with Google Maps import.
    For large number of placemarks, a minimum distance can be specified so close placemarks from one another will not be exported.
    '''
    
    # Member variables
    MapName = ""
    MapDescription = ""
    _PlacemarkList = []
    _PlacemarkListIsOrdered = False
    MinDistanceBetweenPlacemarks = 0  # minimum distance there as to be from previous point for current placemark to be exported.
    
    def __init__(self, MapName:str):
        '''
        Constructor
        '''
        self.MapName = MapName
    
    def __repr__(self):
        return "KML({})".format(self.MapName)
    
    def __str__(self):
        return "This is My KML : " + self.MapName
    
    def ScanFolder(self, Folder:str):
        """
        Scans folders recursively to build a list of compatible image files, extract exif data and returns the number of imported files (that had gps information).
        :param Folder: (string)
        :rtype: int
        """
        # Get list of files
        from pathlib import Path
        BaseFolder = Path(Folder)
        FileTypes = ("*.jpg", "*.jpeg", "*.dng")
        FileList = []
        for FileType in FileTypes:
            FileList.extend(BaseFolder.glob('**/' + FileType))  # # ** allows to parse forlder recursively
        import exifread
        # import os
        NbFiles = 0
        for MyFile in FileList:
            try:
                tags = exifread.process_file(open(str(MyFile), 'rb'))
            except:
                print("\tCould not read exif from file " + str(MyFile))
                
            try:
                MyLat = self._convert_to_degress(tags['GPS GPSLatitude'])
                if (tags["GPS GPSLatitudeRef"].values[0] != "N"):
                    MyLat = -MyLat
                MyLon = self._convert_to_degress(tags['GPS GPSLongitude'])
                if (tags["GPS GPSLongitudeRef"].values[0] != "E"):
                    MyLon = -MyLon
                # FilePath , FileName = os.path.split(MyFile)
                # BasePath, FirstFolder = os.path.split(FilePath)
                self._AddPlacemark(MyLat, MyLon, str(MyFile), Folder)
                NbFiles += 1
                
            except:
                print("\tCould not extract GPS info from file " + str(MyFile))
        
        print(str(NbFiles) + " files have coordinates in folder " + Folder)
        return NbFiles
    
    def _AddPlacemark(self, Latitude:float, Longitude:float, Name:str="", Folder:str=""):
        self._PlacemarkList.append({"Latitude":Latitude, "Longitude":Longitude, "Name":Name, "Folder":Folder})
        _PlacemarkListIsOrdered = False
        
    def _GetKMLString(self):
        
        # use ElementTree for building XML.
        # Use MiniDOM to format XML for readability
        
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        # create the file structure
        root = ET.Element('kml')
        root.set("xmlns", "http://www.opengis.net/kml/2.2")
        Document = ET.SubElement(root, 'Document')
        Name = ET.SubElement(Document, "name")
        Name.text = self.MapName
        description = ET.SubElement(Document, "description")
        description.text = self.MapDescription

        # Sort List prior to export
        self._ReorderPlacemarks()
            
        # Create first folder element
        Folder = ET.SubElement(Document, "Folder")
        FolderName = ET.SubElement(Folder, "name")
        FolderName.text = self._PlacemarkList[0]["Folder"]
        
        import os
        NbFilesToExport = 0
        for MyCoord in self._PlacemarkList:
            if (MyCoord["Folder"] != FolderName.text):
                # Create new folder if different
                Folder = ET.SubElement(Document, "Folder")
                FolderName = ET.SubElement(Folder, "name")
                FolderName.text = MyCoord["Folder"]
                
            if (MyCoord["Export"]):
                MyPlacemark = ET.SubElement(Folder, "Placemark")
                if MyCoord["Name"] != "":
                    FilePath , FileName = os.path.split(MyCoord["Name"])
                    MyName = ET.SubElement(MyPlacemark, "name")
                    MyName.text = FileName
                    Mydesc = ET.SubElement(MyPlacemark, "description")
                    Mydesc.text = FilePath
                
                MyPoint = ET.SubElement(MyPlacemark, "Point")
                MyCoordinate = ET.SubElement(MyPoint, "coordinates")
                MyCoordinate.text = str(MyCoord["Longitude"]) + "," + str(MyCoord["Latitude"])
                NbFilesToExport += 1
        
        print(str(NbFilesToExport) + " placemarks exported to KML.")
        
        # create a new XML file with the results
        XMLString = ET.tostring(root, encoding='unicode')
        try:
            XMLString = minidom.parseString(XMLString).toprettyxml()
        except:
            print ("Problems converting to Pretty XML (minidom)...")
        return XMLString
    
    def SaveKMLFile(self, path:str):
        KMLString = self._GetKMLString()
        try:
            with open(path, "w") as MyFile:
                MyFile.write(KMLString)
        except:
            print("\tCould not save KML file")
            return False
        
        return True
    
    def _ReorderPlacemarks(self):
        """
        Sorts list based on Folder and latitude and calculates distance from previous point.
        """
        if (not self._PlacemarkListIsOrdered):  # sort only if not already sorted
            # Sort List in order to calculate distance between points.
            self._PlacemarkList = sorted(self._PlacemarkList, key=lambda i: (i["Folder"], i['Latitude']))
            LastLongitude = 0
            LastLatitude = 0
            for MyCoord in self._PlacemarkList:
                MyCoord["Distance"] = self._DistanceBetweenPlacemarks(MyCoord["Latitude"], MyCoord["Longitude"], LastLatitude, LastLongitude)
                LastLongitude = MyCoord["Longitude"]
                LastLatitude = MyCoord["Latitude"]
            self._PlacemarkListIsOrdered = True
            self._FilterPlacemarks()  # recalculate placemarks to be exported
    
    def _FilterPlacemarks(self):
        '''
        Functions that will sort Placemark list and tag each placemark to be exported based on the MinDistance parameter.
        pMinDistance : distance in meters
        '''
        
        print("\tMin Distance Between Placemarks set to " + str(self.MinDistanceBetweenPlacemarks) + " meters.")
            
        ExportCount = 0
        for MyCoord in self._PlacemarkList:
            if MyCoord["Distance"] < self.MinDistanceBetweenPlacemarks:
                MyCoord["Export"] = False
            else:
                MyCoord["Export"] = True
                ExportCount += 1
        
        print("\t" + str(ExportCount) + " / " + str(len(self._PlacemarkList)) + " placemarks marked to export.")
        return  ExportCount
        
    def _convert_to_degress(self, value:float):
        """
        Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
        :param value:
        :type value: exifread.utils.Ratio
        :rtype: float
        """
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
    
        return d + (m / 60.0) + (s / 3600.0)
        
    def _DistanceBetweenPlacemarks(self, lat1:float, lon1:float, lat2:float, lon2:float):
        import math
        R = 6378.137  # // Radius of earth in KM
        dLat = lat2 * math.pi / 180 - lat1 * math.pi / 180
        dLon = lon2 * math.pi / 180 - lon1 * math.pi / 180
        a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(lat1 * math.pi / 180) * math.cos(lat2 * math.pi / 180) * math.sin(dLon / 2) * math.sin(dLon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = R * c
        return d * 1000  # // meters
