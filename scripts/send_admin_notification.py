#!/usr/bin/env python3
"""
Simple script to send admin notifications.

Usage:
    python scripts/send_admin_notification.py <user_id> "Title" "Message"
    python scripts/send_admin_notification.py <user_id> "Title" "Message" --data '{"type":"test"}'

Environment Variables:
    admin_notification_secret: Your admin notification secret key
    API_URL: Base API URL (default: http://localhost:8000)
"""

import argparse
import json
import os
import sys

import dotenv
import requests

dotenv.load_dotenv()


def send_notification(
    user_id: str,
    title: str,
    body: str,
    data: dict | None = None,
    notification_type: str = "other",
    priority: str = "normal",
) -> dict:
    """Send admin notification to a user."""
    admin_notification_secret = os.getenv("ADMIN_NOTIFICATION_SECRET")
    if not admin_notification_secret:
        print("Error: ADMIN_NOTIFICATION_SECRET environment variable not set", file=sys.stderr)
        sys.exit(1)

    api_url = os.getenv("API_URL", "http://localhost:8000")
    url = f"{api_url}/api/v1/notifications/admin-send"

    headers = {
        "X-Admin-Secret": admin_notification_secret,
        "Content-Type": "application/json",
    }

    payload = {
        "user_id": user_id,
        "title": title,
        "body": body,
        "notification_type": notification_type,
        "priority": priority,
    }

    if data:
        payload["data"] = data

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Request Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Send admin notification to a user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple notification
  python send_admin_notification.py 6af011a7-44c1-4313-890a-6f973966b10d "Test" "Hello"

  # With custom data
  python send_admin_notification.py USER_ID "Title" "Body" --data '{"type":"appointment","id":"123"}'

  # Using environment variables
  export ADMIN_NOTIFICATION_SECRET=your-secret-key
  export API_URL=https://api.medico24.com
  python send_admin_notification.py USER_ID "Title" "Message"
        """,
    )

    parser.add_argument("user_id", help="User ID to send notification to")
    parser.add_argument("title", help="Notification title")
    parser.add_argument("body", help="Notification body/message")
    parser.add_argument(
        "--data",
        type=str,
        help='Custom data payload as JSON string (e.g., \'{"type":"test"}\')',
    )
    parser.add_argument(
        "--type",
        type=str,
        default="other",
        choices=[
            "appointment_reminder",
            "appointment_confirmation",
            "appointment_cancelled",
            "prescription_ready",
            "pharmacy_update",
            "system_announcement",
            "other",
        ],
        help="Notification type (default: other)",
    )
    parser.add_argument(
        "--priority",
        type=str,
        default="normal",
        choices=["low", "normal", "high", "urgent"],
        help="Notification priority (default: normal)",
    )

    args = parser.parse_args()

    # Parse data if provided
    data = None
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --data: {e}", file=sys.stderr)
            sys.exit(1)

    # Send notification
    result = send_notification(
        args.user_id,
        args.title,
        args.body,
        data,
        args.type,
        args.priority,
    )

    # Print result
    print("✅ Notification sent successfully!")
    print(f"   Success: {result['success_count']} device(s)")
    print(f"   Failed:  {result['failure_count']} device(s)")
    print(f"   Message: {result['message']}")


if __name__ == "__main__":
    main()
