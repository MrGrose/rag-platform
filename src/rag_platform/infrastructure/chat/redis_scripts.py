ACQUIRE_SLOT_SCRIPT = """
local now = ARGV[1]
local lease_until = ARGV[2]
local member = ARGV[3]
local global_limit = tonumber(ARGV[4])
local org_limit = tonumber(ARGV[5])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= global_limit then
    return 2
end
if redis.call('ZCARD', KEYS[2]) >= org_limit then
    return 3
end
redis.call('ZADD', KEYS[1], lease_until, member)
redis.call('ZADD', KEYS[2], lease_until, member)
return 1
"""

RESERVE_BUDGET_SCRIPT = """
local estimate = tonumber(ARGV[1])
local daily_limit = tonumber(ARGV[2])
local res_key = ARGV[3]
local payload = ARGV[4]
local res_ttl = tonumber(ARGV[5])
local day_ttl = tonumber(ARGV[6])
local new_total = tonumber(redis.call('INCRBYFLOAT', KEYS[1], estimate))
redis.call('EXPIRE', KEYS[1], day_ttl)
if new_total > daily_limit then
    redis.call('INCRBYFLOAT', KEYS[1], -estimate)
    return 0
end
redis.call('SETEX', res_key, res_ttl, payload)
return 1
"""

SETTLE_BUDGET_SCRIPT = """
local actual = tonumber(ARGV[1])
local reserved = tonumber(ARGV[2])
local payload = redis.call('GET', KEYS[2])
if not payload then
    return 2
end
redis.call('DEL', KEYS[2])
local delta = actual - reserved
if math.abs(delta) > 0.0000001 then
    redis.call('INCRBYFLOAT', KEYS[1], delta)
end
return 1
"""

RELEASE_BUDGET_SCRIPT = """
local reserved = tonumber(ARGV[1])
local payload = redis.call('GET', KEYS[2])
if not payload then
    return 2
end
redis.call('DEL', KEYS[2])
redis.call('INCRBYFLOAT', KEYS[1], -reserved)
return 1
"""
