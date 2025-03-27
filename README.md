# TastyTrade Webhook Service

A webhook service that connects TradingView alerts to TastyTrade brokerage for automated trading.

## Project Overview

This service provides an API endpoint that receives trading signals from TradingView and automatically executes trades on TastyTrade based on those signals.

### Features

- Receives webhook signals from TradingView
- Executes trades on TastyTrade based on signals (long/short)
- Manages positions based on defined trading rules
- Mobile-friendly dashboard for monitoring API calls and trades
- No database required, stateless operation
- Detailed logging for debugging

## Setup Instructions

### Local Development

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up environment variables:
   ```
   export TASTYTRADE_USERNAME="your_username"
   export TASTYTRADE_PASSWORD="your_password"
   export TASTYTRADE_ACCOUNT_ID="your_account_id"
   ```
4. Run the application:
   ```
   uvicorn main:app --reload
   ```
5. Access the dashboard at http://localhost:8000

### Deployment on Render

1. Fork this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `TASTYTRADE_USERNAME`: Your TastyTrade username
   - `TASTYTRADE_PASSWORD`: Your TastyTrade password
   - `TASTYTRADE_ACCOUNT_ID`: Your TastyTrade account ID

## Trading Logic

### Long Signal
When a long signal is received:
1. Check for existing positions
2. Find available cash balance
3. Calculate price of MSTU by buying 1 share
4. Buy as many whole shares of MSTU as possible within:
   - 100% of available cash if other positions exist
   - 50% of available cash if no other positions
5. Close all other positions that existed before the buy

### Short Signal
When a short signal is received:
1. Check for existing positions
2. Find available cash balance
3. Calculate price of MSTZ by buying 1 share
4. Buy as many whole shares of MSTZ as possible within:
   - 100% of available cash if other positions exist
   - 50% of available cash if no other positions
5. Close all other positions that existed before the buy

### Cooldown Period
After a successful trade, the system enters a 12-hour cooldown period during which all incoming signals will result in closing both MSTU and MSTZ positions.

## TradingView Setup

Configure TradingView to send webhook alerts to:
```
https://tt-direct.onrender.com/webhook
```

With the following JSON payload:
```json
{"signal":"long"}
```
or
```json
{"signal":"short"}
```

## Environment Variables

The following environment variables need to be set:

| Variable | Description |
|----------|-------------|
| `TASTYTRADE_USERNAME` | TastyTrade login username |
| `TASTYTRADE_PASSWORD` | TastyTrade login password |
| `TASTYTRADE_ACCOUNT_ID` | TastyTrade account ID |

## Dashboard

The dashboard is available at the root URL:
```
https://tt-direct.onrender.com/
```

It displays:
- Total number of requests
- Successful trades count
- Failed trades count
- Detailed log of all API calls with timestamps in IST 