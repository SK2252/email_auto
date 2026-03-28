import asyncio
import time
import argparse
import random
import sys
import os
from datetime import datetime

# ── Adjust sys.path to allow importing from the project root ──
# Assuming this script is in [project_root]/test_mail/bulk_test_sender.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the project's GmailClient wrapper from mcp_tools
try:
    from mcp_tools.gmail_client import GmailClient
except ImportError:
    print("Error: Could not find mcp_tools.gmail_client. Ensure you are running from the project root.")
    sys.exit(1)

# ────────────────────────────────────────────────────────
# 100 test emails across 8 domains
# ────────────────────────────────────────────────────────
TEST_EMAILS = [
    # ── IT Support (20) ──────────────────────────────────
    {"subject": "Cannot login to VPN from home",              "body": "Hi IT, I've been trying to connect to the VPN since morning but keep getting 'Authentication failed'. My credentials are correct. Please help urgently.",                       "domain": "it_support", "category": "vpn",      "priority": "P1", "sentiment": "frustrated"},
    {"subject": "Laptop screen flickering issue",             "body": "My laptop screen started flickering after the Windows update yesterday. It's making it hard to work. Dell XPS 15.",                                                                "domain": "it_support", "category": "hardware",  "priority": "P2", "sentiment": "neutral"},
    {"subject": "Password reset request",                     "body": "I need to reset my Active Directory password. Account: john.doe@company.com. My current password expired.",                                                                        "domain": "it_support", "category": "password",  "priority": "P3", "sentiment": "neutral"},
    {"subject": "Slow internet in conference room B",         "body": "The WiFi in Conference Room B is extremely slow. We have an important client call in 30 mins. Please check.",                                                                       "domain": "it_support", "category": "network",   "priority": "P1", "sentiment": "urgent"},
    {"subject": "Request: Install Postman on my workstation", "body": "Please install Postman v10 on my workstation. I need it for API testing work. Asset tag: WS-4521.",                                                                               "domain": "it_support", "category": "software",  "priority": "P3", "sentiment": "neutral"},
    {"subject": "Outlook not syncing emails",                 "body": "My Outlook stopped syncing new emails since 9 AM. I've tried restarting but no luck. Running Outlook 365.",                                                                        "domain": "it_support", "category": "software",  "priority": "P2", "sentiment": "frustrated"},
    {"subject": "New employee laptop setup",                  "body": "We have a new joiner starting Monday (Priya Sharma). Please set up a laptop with standard developer image and create AD account.",                                                  "domain": "it_support", "category": "onboarding","priority": "P2", "sentiment": "neutral"},
    {"subject": "Printer on 3rd floor not working",          "body": "The HP LaserJet on the 3rd floor is showing 'Paper Jam' error. I've checked and there's no paper stuck. It needs a technician.",                                                   "domain": "it_support", "category": "hardware",  "priority": "P3", "sentiment": "neutral"},
    {"subject": "VPN keeps disconnecting every 10 mins",     "body": "The VPN disconnects every 10-15 minutes while I'm working from home. Very disruptive to my workflow. Windows 11 laptop.",                                                           "domain": "it_support", "category": "vpn",      "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Access to SharePoint site denied",          "body": "I need access to the Finance SharePoint site: sharepoint.com/sites/finance. My manager Rajesh Kumar has approved this.",                                                            "domain": "it_support", "category": "access",   "priority": "P3", "sentiment": "neutral"},
    {"subject": "Two monitors not displaying",               "body": "My second monitor stopped working after I moved desks. The cable looks fine. Can someone check the display port?",                                                                  "domain": "it_support", "category": "hardware",  "priority": "P3", "sentiment": "neutral"},
    {"subject": "URGENT: Server down - production impacted", "body": "CRITICAL: The app server prod-web-01 is down. Users cannot access the portal. This is a P1 incident. Please escalate immediately.",                                                  "domain": "it_support", "category": "server",   "priority": "P1", "sentiment": "urgent"},
    {"subject": "Request to unblock YouTube for training",   "body": "I need YouTube unblocked for 2 hours today to run a training session. Can IT whitelist it temporarily?",                                                                           "domain": "it_support", "category": "network",   "priority": "P3", "sentiment": "neutral"},
    {"subject": "Antivirus flagging our internal tool",      "body": "Windows Defender is blocking our internal deployment tool. It's a false positive. Please add an exception for C:\\Tools\\deploy.exe.",                                             "domain": "it_support", "category": "security",  "priority": "P2", "sentiment": "neutral"},
    {"subject": "Need admin rights for dev machine",         "body": "I need temporary local admin rights on my dev machine to install Docker. Project deadline is Friday.",                                                                              "domain": "it_support", "category": "access",   "priority": "P2", "sentiment": "urgent"},
    {"subject": "Keyboard spacebar not working",             "body": "The spacebar on my keyboard is stuck. It types 2-3 spaces randomly. Requesting a replacement keyboard.",                                                                           "domain": "it_support", "category": "hardware",  "priority": "P4", "sentiment": "neutral"},
    {"subject": "Teams video not working in meetings",       "body": "My camera works in other apps but not in Microsoft Teams. Other team members can't see me during calls.",                                                                           "domain": "it_support", "category": "software",  "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Backup drive not being detected",           "body": "The USB backup drive I use for weekly backups is no longer detected by my laptop. Is it faulty or a driver issue?",                                                                 "domain": "it_support", "category": "hardware",  "priority": "P3", "sentiment": "neutral"},
    {"subject": "Internet very slow since yesterday",        "body": "My internet speed dropped from ~100Mbps to ~5Mbps since yesterday afternoon. Other people at my desk seem fine.",                                                                   "domain": "it_support", "category": "network",   "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Software license expired - need renewal",  "body": "My Adobe Acrobat Pro license expired today. I use it daily for PDF work. Please renew ASAP.",                                                                                       "domain": "it_support", "category": "software",  "priority": "P2", "sentiment": "neutral"},

    # ── HR (15) ──────────────────────────────────────────
    {"subject": "Annual leave application - Dec 23-27",      "body": "Hi HR, I'd like to apply for annual leave from December 23 to December 27 (5 days). I have sufficient leave balance. Please approve.",                                            "domain": "hr", "category": "leave",      "priority": "P3", "sentiment": "positive"},
    {"subject": "Salary slip not received for November",     "body": "I haven't received my November salary slip yet. All previous months came fine. Please check and resend to my email.",                                                               "domain": "hr", "category": "payroll",    "priority": "P2", "sentiment": "neutral"},
    {"subject": "Maternity leave policy question",           "body": "I'm expecting in April and want to understand the maternity leave policy - duration, pay, and the process to apply.",                                                               "domain": "hr", "category": "policy",     "priority": "P3", "sentiment": "positive"},
    {"subject": "Work from home policy clarification",       "body": "Can you clarify the current WFH policy? Our team lead says 3 days office but HR circular says 2. Which is correct?",                                                               "domain": "hr", "category": "policy",     "priority": "P3", "sentiment": "neutral"},
    {"subject": "Onboarding documents for new joiner",       "body": "I've just joined as a Senior Developer. Please let me know the list of documents I need to submit for full onboarding.",                                                            "domain": "hr", "category": "onboarding", "priority": "P2", "sentiment": "positive"},
    {"subject": "Tax declaration Form 12BB",                 "body": "I need to submit my tax-saving declaration for FY 2024-25. What's the deadline and where do I submit Form 12BB?",                                                                  "domain": "hr", "category": "payroll",    "priority": "P2", "sentiment": "neutral"},
    {"subject": "Sick leave - Doctor's certificate attached","body": "I was hospitalized for 3 days (Oct 10-12). Attaching medical certificate. Please mark as medical leave not casual leave.",                                                          "domain": "hr", "category": "leave",      "priority": "P3", "sentiment": "neutral"},
    {"subject": "Request for experience letter",             "body": "I've resigned and my last day is Nov 30. Please process my experience letter and relieving letter by then.",                                                                        "domain": "hr", "category": "offboarding","priority": "P2", "sentiment": "neutral"},
    {"subject": "Grievance: Unfair performance rating",      "body": "I want to formally raise a grievance about my Q3 performance rating. I believe it was unfair and not aligned with my contributions.",                                               "domain": "hr", "category": "grievance",  "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Comp-off for working on Diwali",            "body": "I worked on Diwali (Nov 1) as requested by my manager. Requesting 1 comp-off day. Manager: Anitha Rajan.",                                                                         "domain": "hr", "category": "leave",      "priority": "P3", "sentiment": "neutral"},
    {"subject": "Health insurance card not received",        "body": "My health insurance card was supposed to arrive last month but I haven't received it yet. Employee ID: EMP-4422.",                                                                  "domain": "hr", "category": "benefits",   "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Internship certificate request",            "body": "My 3-month internship ended on Oct 31. Requesting an internship completion certificate for my job applications.",                                                                   "domain": "hr", "category": "offboarding","priority": "P3", "sentiment": "positive"},
    {"subject": "Office relocation - need clarity",         "body": "We heard the Chennai office is relocating in January. What is the new address and will there be transport support?",                                                                 "domain": "hr", "category": "policy",     "priority": "P3", "sentiment": "neutral"},
    {"subject": "Variable pay not included in September",   "body": "My Q2 variable pay (approved by manager) was supposed to be included in September salary but it's missing.",                                                                        "domain": "hr", "category": "payroll",    "priority": "P1", "sentiment": "frustrated"},
    {"subject": "Training reimbursement claim",              "body": "I attended an approved external training on Oct 20. Total cost: Rs 8,500. Attaching receipts for reimbursement as per policy.",                                                     "domain": "hr", "category": "benefits",   "priority": "P3", "sentiment": "positive"},

    # ── Customer Support (15) ────────────────────────────
    {"subject": "Order #ORD-88921 not delivered",            "body": "My order was supposed to arrive 3 days ago. The tracking says 'Out for delivery' since Monday. Please investigate.",                                                               "domain": "customer_support", "category": "delivery",  "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Wrong item received in my order",           "body": "I ordered a Blue T-shirt (Size L) but received a Red one (Size M). Please arrange a replacement or refund.",                                                                       "domain": "customer_support", "category": "refund",    "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Request refund for cancelled subscription", "body": "I cancelled my Premium subscription on Oct 15 but was still charged for November. Please refund Rs 499.",                                                                          "domain": "customer_support", "category": "billing",   "priority": "P2", "sentiment": "frustrated"},
    {"subject": "App crashing on Android 14",                "body": "Your mobile app crashes every time I try to open the cart on my Pixel 8 (Android 14). This started after the latest update.",                                                      "domain": "customer_support", "category": "bug",       "priority": "P1", "sentiment": "frustrated"},
    {"subject": "Double charged on my credit card",          "body": "I was charged twice for the same order (Txn IDs: TXN990123 and TXN990124). Please reverse the duplicate charge immediately.",                                                       "domain": "customer_support", "category": "billing",   "priority": "P1", "sentiment": "urgent"},
    {"subject": "How to upgrade my plan?",                   "body": "I'm currently on the Basic plan and want to upgrade to Pro. What are the steps and will my data be retained?",                                                                     "domain": "customer_support", "category": "account",   "priority": "P3", "sentiment": "positive"},
    {"subject": "Password reset not working",                "body": "I'm trying to reset my password but the reset email is not arriving. I've checked spam. Account email: user@example.com",                                                          "domain": "customer_support", "category": "account",   "priority": "P2", "sentiment": "neutral"},
    {"subject": "Product arrived damaged",                   "body": "The product I received has a cracked casing. It was clearly damaged in transit. I need a replacement or full refund.",                                                              "domain": "customer_support", "category": "refund",    "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Invoice not matching actual amount",        "body": "The invoice I received shows Rs 12,000 but I was charged Rs 13,500. Please correct the invoice or explain the difference.",                                                         "domain": "customer_support", "category": "billing",   "priority": "P2", "sentiment": "neutral"},
    {"subject": "Great product, requesting more features",  "body": "I love the product! One suggestion: can you add dark mode and CSV export? Would make it even better for our team.",                                                                  "domain": "customer_support", "category": "feedback",  "priority": "P4", "sentiment": "positive"},
    {"subject": "Account locked after failed attempts",     "body": "My account got locked after 3 failed login attempts. I need it unlocked. I can verify identity via OTP on my registered mobile.",                                                   "domain": "customer_support", "category": "account",   "priority": "P2", "sentiment": "neutral"},
    {"subject": "Coupon code not applying at checkout",     "body": "I have a valid coupon code SAVE20 but it's showing 'Invalid code' at checkout. The code is valid till Dec 31.",                                                                     "domain": "customer_support", "category": "billing",   "priority": "P3", "sentiment": "frustrated"},
    {"subject": "When will my feature request be done?",    "body": "I submitted a feature request 3 months ago (Ticket #FR-2231). Can you give me an update on the timeline?",                                                                         "domain": "customer_support", "category": "feedback",  "priority": "P4", "sentiment": "neutral"},
    {"subject": "Service outage on Nov 5 - need credit",   "body": "Your service was down for 4 hours on Nov 5. This affected our business operations. We would like a service credit.",                                                                 "domain": "customer_support", "category": "billing",   "priority": "P2", "sentiment": "frustrated"},
    {"subject": "Subscription renewal issue",               "body": "My subscription auto-renewed even though I had cancelled auto-renew from settings. Please cancel and refund.",                                                                      "domain": "customer_support", "category": "billing",   "priority": "P2", "sentiment": "frustrated"},

    # ── Finance (12) ─────────────────────────────────────
    {"subject": "Invoice INV-2024-445 approval pending",    "body": "Invoice from TechVendor (INV-2024-445) for Rs 1,25,000 has been pending approval for 2 weeks. Please expedite as vendor is following up.",                                          "domain": "finance", "category": "invoice",       "priority": "P2", "sentiment": "neutral"},
    {"subject": "Travel expense reimbursement - Bangalore", "body": "Attaching receipts for my Bangalore trip (Oct 18-20): flight Rs 8,200, hotel Rs 6,400, local travel Rs 1,200. Total: Rs 15,800.",                                                   "domain": "finance", "category": "reimbursement", "priority": "P3", "sentiment": "neutral"},
    {"subject": "Budget allocation Q1 2025 request",        "body": "I'm submitting our team's Q1 2025 budget request. Infra: Rs 4L, Training: Rs 1.5L, Tools: Rs 2L. Please review and approve.",                                                       "domain": "finance", "category": "budget",        "priority": "P2", "sentiment": "neutral"},
    {"subject": "PO #PO-5521 not reflecting in system",     "body": "Purchase Order PO-5521 was approved by VP on Oct 25 but it's still not showing in the finance system. Vendor needs confirmation.",                                                  "domain": "finance", "category": "purchase_order","priority": "P2", "sentiment": "neutral"},
    {"subject": "Foreign currency payment approval needed", "body": "We need to pay $12,500 to US vendor for software licenses. Please initiate wire transfer approval. Invoice attached.",                                                               "domain": "finance", "category": "payment",       "priority": "P2", "sentiment": "urgent"},
    {"subject": "Advance salary request",                   "body": "Due to personal emergency I need an advance of Rs 50,000 against my November salary. I'll have it deducted over 2 months.",                                                         "domain": "finance", "category": "payroll",       "priority": "P2", "sentiment": "urgent"},
    {"subject": "Vendor payment overdue - legal risk",      "body": "Payment to CloudInfra vendor (due Oct 31) is now 15 days overdue. They have sent a legal notice. Please process immediately.",                                                       "domain": "finance", "category": "payment",       "priority": "P1", "sentiment": "urgent"},
    {"subject": "Monthly expense report submission",        "body": "Attaching October expense report with all receipts. Total: Rs 22,450. Includes client entertainment (Rs 8,000) pre-approved by manager.",                                           "domain": "finance", "category": "reimbursement", "priority": "P3", "sentiment": "neutral"},
    {"subject": "GST certificate needed urgently",          "body": "Our CA needs the company's latest GST certificate for a tender submission today by 5 PM. Please share ASAP.",                                                                       "domain": "finance", "category": "compliance",    "priority": "P1", "sentiment": "urgent"},
    {"subject": "Annual audit document request",            "body": "Our auditors need last 3 years P&L statements and balance sheets by Nov 20. Please prepare and share with our audit team.",                                                          "domain": "finance", "category": "audit",         "priority": "P2", "sentiment": "neutral"},
    {"subject": "Petty cash reimbursement request",         "body": "Office supplies bought for pantry and stationery: Rs 3,240. Receipts attached. Please credit to my account.",                                                                       "domain": "finance", "category": "reimbursement", "priority": "P4", "sentiment": "neutral"},
    {"subject": "Question on new expense policy",           "body": "The new expense policy says 'receipts mandatory above Rs 500' - does this apply to per-day meal allowance during travel as well?",                                                   "domain": "finance", "category": "policy",        "priority": "P4", "sentiment": "neutral"},

    # ── Legal (10) ───────────────────────────────────────
    {"subject": "NDA needed for new vendor Softech",        "body": "We're onboarding Softech as a vendor and need an NDA signed before sharing specs. Please send standard NDA template.",                                                              "domain": "legal", "category": "nda",        "priority": "P2", "sentiment": "neutral"},
    {"subject": "Contract renewal - AWS Enterprise",        "body": "Our AWS Enterprise Agreement expires Dec 31. Legal review needed before we renew. Contract value: $240,000/year.",                                                                  "domain": "legal", "category": "contract",   "priority": "P1", "sentiment": "urgent"},
    {"subject": "GDPR compliance question on user data",    "body": "Our new feature stores user location data. Do we need consent banners? What's the retention limit under GDPR?",                                                                    "domain": "legal", "category": "compliance", "priority": "P2", "sentiment": "neutral"},
    {"subject": "Customer threatening legal action",        "body": "Customer ref: CUST-8821 is threatening to sue over a data privacy issue. Please involve legal counsel immediately.",                                                               "domain": "legal", "category": "dispute",    "priority": "P1", "sentiment": "urgent"},
    {"subject": "IP ownership clause in new offer letter",  "body": "Our new offer letter has a clause saying all personal projects belong to the company. Can legal review and clarify the scope?",                                                     "domain": "legal", "category": "contract",   "priority": "P2", "sentiment": "neutral"},
    {"subject": "Terms of service update review",           "body": "We're updating our ToS for the new product launch. Need legal review within this week. Draft doc attached.",                                                                       "domain": "legal", "category": "compliance", "priority": "P2", "sentiment": "neutral"},
    {"subject": "Patent filing for our AI algorithm",       "body": "Our R&D team has developed a novel AI routing algorithm. Want to file a patent. What's the process and estimated timeline?",                                                        "domain": "legal", "category": "ip",         "priority": "P3", "sentiment": "positive"},
    {"subject": "Employee moonlighting policy",             "body": "Two employees are found to be working part-time for a competitor. Is this a policy violation? What action can be taken?",                                                           "domain": "legal", "category": "hr_legal",   "priority": "P2", "sentiment": "neutral"},
    {"subject": "Software license compliance audit",        "body": "Microsoft has requested a software license compliance audit for Nov 15. We need legal and IT to coordinate on this.",                                                              "domain": "legal", "category": "compliance", "priority": "P2", "sentiment": "neutral"},
    {"subject": "Non-compete clause enforceability",        "body": "A former employee has joined a competitor within 6 months of leaving. Our contract has a non-compete clause. Can we enforce it?",                                                  "domain": "legal", "category": "dispute",    "priority": "P2", "sentiment": "urgent"},

    # ── Sales (10) ───────────────────────────────────────
    {"subject": "Demo request from TataConsultancy",        "body": "TCS wants a product demo for their team of 50. They're evaluating 3 vendors. This is a high-value opportunity (~Rs 2Cr). Please schedule ASAP.",                                    "domain": "sales", "category": "demo",    "priority": "P1", "sentiment": "positive"},
    {"subject": "Pricing for enterprise plan - 500 users",  "body": "Client Infosys is asking for enterprise pricing for 500 users. They want a proposal by Friday. Can sales ops prepare the quote?",                                                   "domain": "sales", "category": "pricing", "priority": "P1", "sentiment": "urgent"},
    {"subject": "Follow-up: Proposal sent last week",       "body": "Just following up on the proposal I sent to Wipro last Tuesday. Have they reviewed it? Should I reach out to their procurement team?",                                              "domain": "sales", "category": "followup","priority": "P2", "sentiment": "neutral"},
    {"subject": "Client asking for custom integration",     "body": "HCL wants Salesforce integration as part of their purchase. Is this in scope? What's the additional cost and timeline?",                                                            "domain": "sales", "category": "custom",  "priority": "P2", "sentiment": "neutral"},
    {"subject": "Q4 pipeline review - need updated data",  "body": "Board meeting is next week and I need the updated Q4 pipeline numbers, win rate and deal sizes by EOD today.",                                                                       "domain": "sales", "category": "reporting","priority": "P1", "sentiment": "urgent"},
    {"subject": "Prospect asking for ROI calculator",       "body": "Prospect Mahindra Finance wants an ROI calculator to justify the purchase internally. Can we share our standard ROI model?",                                                        "domain": "sales", "category": "demo",    "priority": "P2", "sentiment": "positive"},
    {"subject": "Discount approval request - 25% off",     "body": "Client Hexaware is asking for 25% discount to close Q4. The deal is Rs 45L. I need approval from sales director.",                                                                  "domain": "sales", "category": "pricing", "priority": "P2", "sentiment": "neutral"},
    {"subject": "Contract signed - need onboarding started","body": "Great news! Airtel Business just signed the contract. Please trigger the onboarding process. POC: Deepak Nair (deepak@airtel.in).",                                                 "domain": "sales", "category": "won",     "priority": "P2", "sentiment": "positive"},
    {"subject": "Competitor offering lower price",          "body": "Zoho is offering the same features at 40% less to our prospect. Can we revise our pricing strategy or offer additional value?",                                                     "domain": "sales", "category": "pricing", "priority": "P2", "sentiment": "urgent"},
    {"subject": "New RFP from BSNL - 1000 user deal",      "body": "BSNL has sent an RFP for a 1000-user license deal. Deadline to respond is Nov 20. This is a strategic government account.",                                                         "domain": "sales", "category": "rfp",     "priority": "P1", "sentiment": "urgent"},

    # ── Marketing (10) ───────────────────────────────────
    {"subject": "Blog content approval needed",             "body": "I've drafted a blog post on 'AI in Enterprise Email Management'. Need approval from the content team before publishing. Draft attached.",                                           "domain": "marketing", "category": "content",   "priority": "P3", "sentiment": "neutral"},
    {"subject": "Product launch event - venue booking",    "body": "We're planning a product launch event for Jan 15. Need to confirm venue, catering, and AV setup. Budget: Rs 3L.",                                                                   "domain": "marketing", "category": "event",     "priority": "P2", "sentiment": "positive"},
    {"subject": "Google Ads campaign approval - Q4",       "body": "Q4 Google Ads campaign is ready. Budget: Rs 5L. Targeting enterprise IT buyers. Need marketing head approval to go live.",                                                          "domain": "marketing", "category": "campaign",  "priority": "P2", "sentiment": "neutral"},
    {"subject": "Customer testimonial request",             "body": "Reliance Industries agreed to give us a testimonial. Can the marketing team create a case study from their success story?",                                                         "domain": "marketing", "category": "content",   "priority": "P3", "sentiment": "positive"},
    {"subject": "LinkedIn post on product update",         "body": "We just released v2.0. Can marketing schedule a LinkedIn announcement? I've drafted the post text - see attachment.",                                                               "domain": "marketing", "category": "social",    "priority": "P3", "sentiment": "positive"},
    {"subject": "Webinar registration landing page issue", "body": "The webinar registration form on our site is broken - submissions not saving. Webinar is tomorrow! Please fix urgently.",                                                            "domain": "marketing", "category": "digital",   "priority": "P1", "sentiment": "urgent"},
    {"subject": "PR coverage for funding announcement",    "body": "We're announcing our Series B funding next week. Need to coordinate PR strategy - press release, media list, and embargo dates.",                                                    "domain": "marketing", "category": "pr",        "priority": "P2", "sentiment": "positive"},
    {"subject": "Feedback on new brand guidelines",        "body": "The new brand guidelines doc has been shared. Please review and send feedback by Nov 10. Focus on logo usage and color palette sections.",                                           "domain": "marketing", "category": "brand",     "priority": "P3", "sentiment": "neutral"},
    {"subject": "Email newsletter not going out",          "body": "The November newsletter scheduled for 9 AM did not go out. 12,000 subscribers affected. Please check Mailchimp and reschedule.",                                                    "domain": "marketing", "category": "campaign",  "priority": "P1", "sentiment": "urgent"},
    {"subject": "Swag items for conference - order now",  "body": "We're at TechCrunch Bangalore on Dec 5. Need 500 branded pens, 200 T-shirts, 300 tote bags. Please place order by Nov 15.",                                                         "domain": "marketing", "category": "event",     "priority": "P2", "sentiment": "neutral"},

    # ── Others / Edge cases (8) ───────────────────────────
    {"subject": "Re: Re: Re: Meeting tomorrow",             "body": "Sure, see you at 3 PM. Thanks!",                                                                                                                                                   "domain": "others", "category": "ambiguous",  "priority": "P4", "sentiment": "positive"},
    {"subject": "Congratulations on the promotion!",        "body": "Hi team, just wanted to say a big congratulations to Sathish for the well-deserved promotion! You've been an inspiration.",                                                        "domain": "others", "category": "social",     "priority": "P4", "sentiment": "positive"},
    {"subject": "FREE iPhone 15 - claim now!!",             "body": "Congratulations! You've won a FREE iPhone 15. Click here to claim: http://free-iphone-claim.xyz/win?ref=abc123",                                                                   "domain": "others", "category": "spam",       "priority": "P4", "sentiment": "neutral"},
    {"subject": "What's the WiFi password?",                "body": "Hey, I'm visiting from the Hyderabad office. What's the guest WiFi password for the Chennai office?",                                                                              "domain": "others", "category": "ambiguous",  "priority": "P4", "sentiment": "neutral"},
    {"subject": "Office party planning committee",         "body": "Hi all, we're forming a committee for the year-end office party. Volunteers please reply. Budget discussion is on Friday.",                                                         "domain": "others", "category": "social",     "priority": "P4", "sentiment": "positive"},
    {"subject": "Is the canteen open on Saturday?",        "body": "We have to come in this Saturday for the deadline. Will the canteen be operational? Please confirm.",                                                                               "domain": "others", "category": "ambiguous",  "priority": "P4", "sentiment": "neutral"},
    {"subject": "Nigerian prince needs your help",         "body": "Dear friend, I am a prince from Nigeria with $45 million dollars I need to transfer. I need your bank details to proceed.",                                                         "domain": "others", "category": "spam",       "priority": "P4", "sentiment": "neutral"},
    {"subject": "Team lunch poll - vote by EOD",           "body": "Team lunch this Friday! Vote for your preference: 1) Murugan Idli Shop 2) Ponnusamy Hotel 3) Sangeetha Restaurant. Reply with your choice.",                                        "domain": "others", "category": "social",     "priority": "P4", "sentiment": "positive"},
]


async def send_bulk_test_emails(to_address: str, delay: float = 2.0, dry_run: bool = False):
    client = GmailClient()
    
    total = len(TEST_EMAILS)
    sent = 0
    failed = 0
    
    print(f"\n{'='*60}")
    print(f"Bulk Test Email Sender")
    print(f"Target: {to_address}")
    print(f"Total emails: {total} | Delay: {delay}s | Dry run: {dry_run}")
    print(f"{'='*60}\n")

    for i, email in enumerate(TEST_EMAILS, 1):
        tag = f"[{email['domain'].upper()}][{email['category']}][{email['priority']}]"
        subject = f"{tag} {email['subject']}"
        body = (
            f"{email['body']}\n\n"
            f"---\n"
            f"[TEST EMAIL {i:03d}/{total}]\n"
            f"Domain: {email['domain']} | Category: {email['category']}\n"
            f"Priority: {email['priority']} | Sentiment: {email['sentiment']}\n"
            f"Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            if not dry_run:
                # Use send_reply which acts as send_email if thread_id is None
                await client.send_reply(to=to_address, subject=subject, body=body)
            sent += 1
            status = "[DRY]" if dry_run else "[OK] "
            print(f"{status} {i:03d}/{total} {tag} {email['subject'][:45]}")
        except Exception as e:
            failed += 1
            print(f"[ERR] {i:03d}/{total} FAILED: {e}")

        if i < total and not dry_run:
            await asyncio.sleep(delay + random.uniform(-0.3, 0.3))

    print(f"\n{'='*60}")
    print(f"Done! Sent: {sent} | Failed: {failed}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send 100 test emails to validate agent pipeline")
    parser.add_argument("--to",       required=True,        help="Target email address")
    parser.add_argument("--delay",    type=float, default=2.0, help="Delay between emails (seconds)")
    parser.add_argument("--dry-run",  action="store_true",  help="Print without actually sending")
    args = parser.parse_args()

    asyncio.run(send_bulk_test_emails(
        to_address=args.to,
        delay=args.delay,
        dry_run=args.dry_run
    ))
