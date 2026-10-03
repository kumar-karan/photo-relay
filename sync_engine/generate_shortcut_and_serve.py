#!/usr/bin/env python3
"""
Generate an iOS .shortcut file and serve it for 1-tap installation on iPhone.
"""

import plistlib
import os
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

SCRIPT_DIR = Path(__file__).parent.resolve()
STATE_PATH = SCRIPT_DIR / "sync_state.json"
SHORTCUT_PATH = SCRIPT_DIR / "SyncPhotosToSamsung.shortcut"

MAC_IP = None

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def get_cutoff():
    if STATE_PATH.exists():
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
            return data.get("last_synced_timestamp", "2026-08-05T11:50:15")
    return "2026-08-05T11:50:15"

def make_text_action(text, uuid):
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
        "WFWorkflowActionParameters": {
            "WFTextActionText": {
                "Value": {"attachmentsByRange": {}, "string": text},
                "WFSerializationType": "WFTextTokenString"
            },
            "UUID": uuid
        }
    }

def make_url_action(url, uuid):
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.url",
        "WFWorkflowActionParameters": {
            "WFURLActionURL": url,
            "UUID": uuid
        }
    }

def make_download_url_action(method="GET", headers=None, body_type=None, file_variable=None, uuid=""):
    params = {
        "WFHTTPMethod": method,
        "UUID": uuid
    }
    if headers:
        params["WFHTTPHeaders"] = {
            "Value": {"WFDictionaryFieldValueItems": headers},
            "WFSerializationType": "WFDictionaryFieldValue"
        }
    if body_type:
        params["WFHTTPBodyType"] = body_type
    if file_variable:
        params["WFRequestVariable"] = file_variable
    return {
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": params
    }

def build_shortcut(mac_ip):
    """Build the complete shortcut plist structure"""

    cutoff_url = f"http://{mac_ip}:8500/cutoff"
    upload_url = f"http://{mac_ip}:8500/upload"
    trigger_url = f"http://{mac_ip}:8500/trigger_sync"

    actions = []

    # --- Action 1: Get cutoff date from Mac server ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.url",
        "WFWorkflowActionParameters": {
            "WFURLActionURL": cutoff_url,
            "UUID": "A1000001-0001-0001-0001-000000000001"
        }
    })

    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "WFHTTPMethod": "GET",
            "UUID": "A1000001-0001-0001-0001-000000000002"
        }
    })

    # --- Action 2: Get dictionary value for cutoff_date ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.getvalueforkey",
        "WFWorkflowActionParameters": {
            "WFDictionaryKey": "cutoff_date",
            "UUID": "A1000001-0001-0001-0001-000000000003"
        }
    })

    # --- Action 3: Format date ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.format.date",
        "WFWorkflowActionParameters": {
            "WFDateFormatStyle": "Custom",
            "WFDateFormat": "yyyy-MM-dd'T'HH:mm:ss",
            "UUID": "A1000001-0001-0001-0001-000000000004"
        }
    })

    # --- Action 4: Find Photos where Date Taken is after cutoff ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.filter.photos",
        "WFWorkflowActionParameters": {
            "WFContentItemFilter": {
                "Value": {
                    "WFActionParameterFilterPrefix": 1,
                    "WFContentPredicateBoundedDate": False,
                    "WFActionParameterFilterTemplates": [
                        {
                            "Operator": 4,
                            "Values": {
                                "Date": {
                                    "Value": {
                                        "Type": "ActionOutput",
                                        "OutputName": "Formatted Date",
                                        "OutputUUID": "A1000001-0001-0001-0001-000000000004"
                                    },
                                    "WFSerializationType": "WFTextTokenAttachment"
                                },
                                "Unit": 4
                            },
                            "Property": "Creation Date",
                            "Removable": True
                        }
                    ]
                },
                "WFSerializationType": "WFContentPredicateTableTemplate"
            },
            "UUID": "A1000001-0001-0001-0001-000000000005"
        }
    })

    # --- Action 5: Count ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.count",
        "WFWorkflowActionParameters": {
            "UUID": "A1000001-0001-0001-0001-000000000006"
        }
    })

    # --- Action 6: Show notification with count ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
        "WFWorkflowActionParameters": {
            "WFNotificationActionBody": {
                "Value": {
                    "attachmentsByRange": {
                        "{0, 1}": {
                            "Type": "ActionOutput",
                            "OutputName": "Count",
                            "OutputUUID": "A1000001-0001-0001-0001-000000000006"
                        }
                    },
                    "string": "\uFFFC new photos found. Syncing to Samsung..."
                },
                "WFSerializationType": "WFTextTokenString"
            },
            "WFNotificationActionTitle": "iPhone → Samsung Sync",
            "UUID": "A1000001-0001-0001-0001-000000000007"
        }
    })

    # --- Action 7: Re-find photos (need fresh reference after Count) ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.filter.photos",
        "WFWorkflowActionParameters": {
            "WFContentItemFilter": {
                "Value": {
                    "WFActionParameterFilterPrefix": 1,
                    "WFContentPredicateBoundedDate": False,
                    "WFActionParameterFilterTemplates": [
                        {
                            "Operator": 4,
                            "Values": {
                                "Date": {
                                    "Value": {
                                        "Type": "ActionOutput",
                                        "OutputName": "Formatted Date",
                                        "OutputUUID": "A1000001-0001-0001-0001-000000000004"
                                    },
                                    "WFSerializationType": "WFTextTokenAttachment"
                                },
                                "Unit": 4
                            },
                            "Property": "Creation Date",
                            "Removable": True
                        }
                    ]
                },
                "WFSerializationType": "WFContentPredicateTableTemplate"
            },
            "UUID": "A1000001-0001-0001-0001-000000000008"
        }
    })

    # --- Action 8: Repeat with Each photo ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "WFInput": {
                "Value": {
                    "Type": "ActionOutput",
                    "OutputName": "Photos",
                    "OutputUUID": "A1000001-0001-0001-0001-000000000008"
                },
                "WFSerializationType": "WFTextTokenAttachment"
            },
            "GroupingIdentifier": "REPEAT-GROUP-001",
            "WFControlFlowMode": 0,
            "UUID": "A1000001-0001-0001-0001-000000000009"
        }
    })

    # --- Action 9: Inside Repeat - Upload URL ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.url",
        "WFWorkflowActionParameters": {
            "WFURLActionURL": upload_url,
            "UUID": "A1000001-0001-0001-0001-000000000010"
        }
    })

    # --- Action 10: Inside Repeat - POST file ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "WFHTTPMethod": "POST",
            "WFHTTPBodyType": "File",
            "WFRequestVariable": {
                "Value": {
                    "Type": "ActionOutput",
                    "OutputName": "Repeat Item",
                    "OutputUUID": "A1000001-0001-0001-0001-000000000009"
                },
                "WFSerializationType": "WFTextTokenAttachment"
            },
            "UUID": "A1000001-0001-0001-0001-000000000011"
        }
    })

    # --- Action 11: End Repeat ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.repeat.each",
        "WFWorkflowActionParameters": {
            "GroupingIdentifier": "REPEAT-GROUP-001",
            "WFControlFlowMode": 2,
            "UUID": "A1000001-0001-0001-0001-000000000012"
        }
    })

    # --- Action 12: Trigger sync on Mac ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.url",
        "WFWorkflowActionParameters": {
            "WFURLActionURL": trigger_url,
            "UUID": "A1000001-0001-0001-0001-000000000013"
        }
    })

    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
        "WFWorkflowActionParameters": {
            "WFHTTPMethod": "POST",
            "UUID": "A1000001-0001-0001-0001-000000000014"
        }
    })

    # --- Action 13: Final notification ---
    actions.append({
        "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
        "WFWorkflowActionParameters": {
            "WFNotificationActionBody": "All new photos sent to Mac for Samsung sync!",
            "WFNotificationActionTitle": "Sync Complete ✅",
            "UUID": "A1000001-0001-0001-0001-000000000015"
        }
    })

    shortcut = {
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 463140863,
            "WFWorkflowIconGlyphNumber": 59648
        },
        "WFWorkflowClientVersion": "2605.0.5",
        "WFWorkflowOutputContentItemClasses": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowActions": actions,
        "WFWorkflowInputContentItemClasses": [
            "WFAppStoreAppContentItem",
            "WFArticleContentItem",
            "WFContactContentItem",
            "WFDateContentItem",
            "WFEmailAddressContentItem",
            "WFGenericFileContentItem",
            "WFImageContentItem",
            "WFiTunesProductContentItem",
            "WFLocationContentItem",
            "WFDCMapsLinkContentItem",
            "WFAVAssetContentItem",
            "WFPDFContentItem",
            "WFPhoneNumberContentItem",
            "WFRichTextContentItem",
            "WFSafariWebPageContentItem",
            "WFStringContentItem",
            "WFURLContentItem"
        ],
        "WFWorkflowTypes": [],
        "WFWorkflowHasShortcutInputVariables": False
    }

    return shortcut


class ShortcutServer(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_GET(self):
        if self.path == "/cutoff":
            self._set_headers(200)
            cutoff = get_cutoff()
            response = {"cutoff_date": cutoff, "status": "ok"}
            self.wfile.write(json.dumps(response).encode('utf-8'))

        elif self.path == "/shortcut":
            # Serve the .shortcut file for 1-tap install on iPhone
            if SHORTCUT_PATH.exists():
                with open(SHORTCUT_PATH, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="SyncPhotosToSamsung.shortcut"')
                self.send_header('Content-Length', len(data))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Shortcut not generated yet"}).encode('utf-8'))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

    def do_POST(self):
        if self.path == "/upload":
            content_length = int(self.headers.get('Content-Length', 0))
            filename = self.headers.get('X-File-Name', f"iphone_photo_{content_length}.jpg")

            with open(SCRIPT_DIR / "config.json", "r") as f:
                cfg = json.load(f)
            staging_dir = Path(cfg["input_dir"])
            staging_dir.mkdir(parents=True, exist_ok=True)

            out_path = staging_dir / filename
            with open(out_path, 'wb') as f_out:
                f_out.write(self.rfile.read(content_length))

            print(f"📥 Received: {filename} ({content_length} bytes)")
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "success", "file": filename}).encode('utf-8'))

        elif self.path == "/trigger_sync":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "sync_started"}).encode('utf-8'))
            print("\n🚀 Triggering Samsung sync pipeline...")
            import subprocess
            subprocess.Popen(["python3", str(SCRIPT_DIR / "sync_pipeline.py")])
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))


def main():
    mac_ip = get_local_ip()
    port = 8500

    # 1. Generate the .shortcut file
    print("⚙️  Generating iOS Shortcut file...")
    shortcut_data = build_shortcut(mac_ip)
    with open(SHORTCUT_PATH, "wb") as f:
        plistlib.dump(shortcut_data, f, fmt=plistlib.FMT_BINARY)
    print(f"✅ Shortcut saved to: {SHORTCUT_PATH}")

    # 2. Start the server
    print("==========================================================================")
    print(" 📡 iPhone Photo Sync Server + Shortcut Installer")
    print("==========================================================================")
    print(f" Mac IP        : {mac_ip}")
    print(f" Port          : {port}")
    print(f" Cutoff API    : http://{mac_ip}:{port}/cutoff")
    print(f" Upload API    : http://{mac_ip}:{port}/upload")
    print(f" Sync Trigger  : http://{mac_ip}:{port}/trigger_sync")
    print("==========================================================================")
    print(f" 📱 INSTALL SHORTCUT ON IPHONE:")
    print(f"    Open Safari on iPhone and go to:")
    print(f"    http://{mac_ip}:{port}/shortcut")
    print("==========================================================================")

    server = HTTPServer(('0.0.0.0', port), ShortcutServer)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.server_close()

if __name__ == "__main__":
    main()
