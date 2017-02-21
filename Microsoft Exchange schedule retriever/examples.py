# <--- examples

REQ_EXAMPLE_XML = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
   <s:Header>
      <h:DateTimePrecisionType xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types">Seconds</h:DateTimePrecisionType>
      <h:RequestServerVersion Version="Exchange2010_SP2" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types"/>
   </s:Header>
   <s:Body>
      <FindItem Traversal="Shallow" xmlns="http://schemas.microsoft.com/exchange/services/2006/messages">
         <ItemShape>
            <BaseShape xmlns="http://schemas.microsoft.com/exchange/services/2006/types">Default</BaseShape>
            <AdditionalProperties xmlns="http://schemas.microsoft.com/exchange/services/2006/types">
               <FieldURI FieldURI="item:Sensitivity"/>
            </AdditionalProperties>
         </ItemShape>
         <CalendarView StartDate="2017-02-02T17:09:08.967+11:00" EndDate="2017-02-03T17:09:09.099+11:00"/>
         <ParentFolderIds>
            <DistinguishedFolderId Id="calendar" xmlns="http://schemas.microsoft.com/exchange/services/2006/types"/>
         </ParentFolderIds>
      </FindItem>
   </s:Body>
</s:Envelope>
'''

RESP_EXAMPLE_XML = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Header>
        <h:ServerVersionInfo MajorVersion="15" MinorVersion="1" MajorBuildNumber="860" MinorBuildNumber="27" Version="V2016_10_10" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
    </s:Header>
    <s:Body>
        <m:FindItemResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
            <m:ResponseMessages>
                <m:FindItemResponseMessage ResponseClass="Success">
                    <m:ResponseCode>NoError</m:ResponseCode>
                    <m:RootFolder TotalItemsInView="3" IncludesLastItemInRange="true">
                        <t:Items>
                            <t:CalendarItem>
                                <t:ItemId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQFRAAgI1Er+bl/AAEYAAAAAeirp9k9VGku0njC/1lrpHQcAipU2FStC9UuDW8jkOLEm0AAAAAABDgAAipU2FStC9UuDW8jkOLEm0AAAV1crjQAAEA==" ChangeKey="DwAAABYAAACKlTYVK0L1S4NbyOQ4sSbQAALVH0l1"/>
                                <t:Subject>Monthly Meeting</t:Subject>
                                <t:Sensitivity>Normal</t:Sensitivity>
                                <t:HasAttachments>false</t:HasAttachments>
                                <t:IsAssociated>false</t:IsAssociated>
                                <t:Start>2017-02-02T05:30:00Z</t:Start>
                                <t:End>2017-02-02T06:15:00Z</t:End>
                                <t:LegacyFreeBusyStatus>Busy</t:LegacyFreeBusyStatus>
                                <t:Location>Hyde Street Office</t:Location>
                                <t:CalendarItemType>Exception</t:CalendarItemType>
                                <t:Organizer>
                                    <t:Mailbox>
                                        <t:Name>XXXX Summers</t:Name>
                                        <t:EmailAddress>/O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP (FYDIBOHF23SPDLT)/CN=RECIPIENTS/CN=62B57D2CA0B24A86A54037027CDAAF24-XXXX.SUMME</t:EmailAddress>
                                        <t:RoutingType>EX</t:RoutingType>
                                        <t:MailboxType>OneOff</t:MailboxType>
                                    </t:Mailbox>
                                </t:Organizer>
                            </t:CalendarItem>
                            <t:CalendarItem>
                                <t:ItemId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQBGAAAAAAB6Kun2T1UaS7SeML/WWukdBwCKlTYVK0L1S4NbyOQ4sSbQAAAAAAEOAACKlTYVK0L1S4NbyOQ4sSbQAALUuSskAAA=" ChangeKey="DwAAABYAAACKlTYVK0L1S4NbyOQ4sSbQAALVH0l2"/>
                                <t:Subject>Instant Meeting</t:Subject>
                                <t:Sensitivity>Normal</t:Sensitivity>
                                <t:HasAttachments>false</t:HasAttachments>
                                <t:IsAssociated>false</t:IsAssociated>
                                <t:Start>2017-02-02T06:26:32Z</t:Start>
                                <t:End>2017-02-02T07:00:00Z</t:End>
                                <t:LegacyFreeBusyStatus>Busy</t:LegacyFreeBusyStatus>
                                <t:CalendarItemType>Single</t:CalendarItemType>
                                <t:Organizer>
                                    <t:Mailbox>
                                        <t:Name>Other</t:Name>
                                        <t:EmailAddress>/O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP (FYDIBOHF23SPDLT)/CN=RECIPIENTS/CN=62B57D2CA0B24A86A54037027CDAAF24-XXXX.SUMME</t:EmailAddress>
                                        <t:RoutingType>EX</t:RoutingType>
                                        <t:MailboxType>OneOff</t:MailboxType>
                                    </t:Mailbox>
                                </t:Organizer>
                            </t:CalendarItem>
                            <t:CalendarItem>
                                <t:ItemId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQFRAAgI1EvHmMmAAEYAAAAAeirp9k9VGku0njC/1lrpHQcAipU2FStC9UuDW8jkOLEm0AAAAAABDgAAipU2FStC9UuDW8jkOLEm0AAAPMUtCgAAEA==" ChangeKey="DwAAABYAAACKlTYVK0L1S4NbyOQ4sSbQAALHy1u1"/>
                                <t:Subject>Other Catch-up</t:Subject>
                                <t:Sensitivity>Normal</t:Sensitivity>
                                <t:HasAttachments>false</t:HasAttachments>
                                <t:IsAssociated>false</t:IsAssociated>
                                <t:Start>2017-02-03T04:00:00Z</t:Start>
                                <t:End>2017-02-03T06:00:00Z</t:End>
                                <t:LegacyFreeBusyStatus>Busy</t:LegacyFreeBusyStatus>
                                <t:Location>Office</t:Location>
                                <t:CalendarItemType>Occurrence</t:CalendarItemType>
                                <t:Organizer>
                                    <t:Mailbox>
                                        <t:Name>XXXX Summers</t:Name>
                                        <t:EmailAddress>/O=EXCHANGELABS/OU=EXCHANGE ADMINISTRATIVE GROUP (FYDIBOHF23SPDLT)/CN=RECIPIENTS/CN=62B57D2CA0B24A86A54037027CDAAF24-XXXX.SUMME</t:EmailAddress>
                                        <t:RoutingType>EX</t:RoutingType>
                                        <t:MailboxType>OneOff</t:MailboxType>
                                    </t:Mailbox>
                                </t:Organizer>
                            </t:CalendarItem>
                        </t:Items>
                    </m:RootFolder>
                </m:FindItemResponseMessage>
            </m:ResponseMessages>
        </m:FindItemResponse>
    </s:Body>
</s:Envelope>'''

REQ_EXAMPLE_GETFOLDERS_XML = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Header>
        <h:DateTimePrecisionType xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types">Seconds</h:DateTimePrecisionType>
        <h:RequestServerVersion Version="Exchange2010_SP2" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types"/>
    </s:Header>
    <s:Body>
        <FindFolder Traversal="Deep" xmlns="http://schemas.microsoft.com/exchange/services/2006/messages">
            <FolderShape>
                <BaseShape xmlns="http://schemas.microsoft.com/exchange/services/2006/types">Default</BaseShape>
            </FolderShape>
            <ParentFolderIds>
                <DistinguishedFolderId Id="calendar" xmlns="http://schemas.microsoft.com/exchange/services/2006/types"/>
            </ParentFolderIds>
        </FindFolder>
    </s:Body>
</s:Envelope>'''

RESP_EXAMPLE_GETFOLDERS_XML = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Header>
        <h:ServerVersionInfo MajorVersion="15" MinorVersion="1" MajorBuildNumber="888" MinorBuildNumber="27" Version="V2017_01_07" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>
    </s:Header>
    <s:Body>
        <m:FindFolderResponse xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
            <m:ResponseMessages>
                <m:FindFolderResponseMessage ResponseClass="Success">
                    <m:ResponseCode>NoError</m:ResponseCode>
                    <m:RootFolder TotalItemsInView="3" IncludesLastItemInRange="true">
                        <t:Folders>
                            <t:CalendarFolder>
                                <t:FolderId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQAuAAAAAAB6Kun2T1UaS7SeML/WWukdAQCKlTYVK0L1S4NbyOQ4sSbQAALZU7fhAAA=" ChangeKey="AgAAABQAAAD8vWH6ONfhT7eqjuZ+hFA+AAAEQg=="/>
                                <t:DisplayName>IM</t:DisplayName>
                                <t:TotalCount>0</t:TotalCount>
                                <t:ChildFolderCount>0</t:ChildFolderCount>
                            </t:CalendarFolder>
                            <t:CalendarFolder>
                                <t:FolderId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQAuAAAAAAB6Kun2T1UaS7SeML/WWukdAQCKlTYVK0L1S4NbyOQ4sSbQAALZU7ffAAA=" ChangeKey="AgAAABQAAAD8vWH6ONfhT7eqjuZ+hFA+AAAEQA=="/>
                                <t:DisplayName>MM</t:DisplayName>
                                <t:TotalCount>2</t:TotalCount>
                                <t:ChildFolderCount>0</t:ChildFolderCount>
                            </t:CalendarFolder>
                            <t:CalendarFolder>
                                <t:FolderId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQAuAAAAAAB6Kun2T1UaS7SeML/WWukdAQCKlTYVK0L1S4NbyOQ4sSbQAALZU7fgAAA=" ChangeKey="AgAAABQAAAD8vWH6ONfhT7eqjuZ+hFA+AAAEQQ=="/>
                                <t:DisplayName>MV</t:DisplayName>
                                <t:TotalCount>0</t:TotalCount>
                                <t:ChildFolderCount>0</t:ChildFolderCount>
                            </t:CalendarFolder>
                        </t:Folders>
                    </m:RootFolder>
                </m:FindFolderResponseMessage>
            </m:ResponseMessages>
        </m:FindFolderResponse>
    </s:Body>
</s:Envelope>
'''

REQ_EXAMPLE_GETBYFOLDERID_XML = '''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Header>
        <h:DateTimePrecisionType xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types">Seconds</h:DateTimePrecisionType>
        <h:RequestServerVersion Version="Exchange2010_SP2" xmlns:h="http://schemas.microsoft.com/exchange/services/2006/types"/>
    </s:Header>
    <s:Body>
        <FindItem Traversal="Shallow" xmlns="http://schemas.microsoft.com/exchange/services/2006/messages">
            <ItemShape>
                <BaseShape xmlns="http://schemas.microsoft.com/exchange/services/2006/types">Default</BaseShape>
                <AdditionalProperties xmlns="http://schemas.microsoft.com/exchange/services/2006/types">
                    <FieldURI FieldURI="item:Sensitivity"/>
                </AdditionalProperties>
            </ItemShape>
            <CalendarView StartDate="2017-02-09T15:44:11.463+11:00" EndDate="2017-02-15T11:00:00.000+11:00"/>
            <ParentFolderIds>
                <FolderId Id="AAMkAGVkOTNmM2I5LTkzM2EtNGE2NC05N2JjLTFhOTU2ZmJkOTIzOQAuAAAAAAB6Kun2T1UaS7SeML/WWukdAQCKlTYVK0L1S4NbyOQ4sSbQAALZU7ffAAA=" ChangeKey="AgAAABQAAAD8vWH6ONfhT7eqjuZ+hFA+AAAEQA==" xmlns="http://schemas.microsoft.com/exchange/services/2006/types"/>
            </ParentFolderIds>
        </FindItem>
    </s:Body>
</s:Envelope>
'''

# examples --->