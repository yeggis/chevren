-- test
local utils = require 'mp.utils'

local function get_video_id()
    local path = mp.get_property("path")
    if not path then return nil end

    -- YouTube URL veya video_id çıkarımı
    local v = path:match("v=([%w_-]+)")
    if not v then
        v = path:match("youtu.be/([%w_-]+)")
    end
    
    if v then return v end

    -- Lokal dosya
    local filename = mp.get_property("filename/no-ext")
    if filename then
        -- Python Path.stem[:40] ile uyumlu
        return filename:sub(1, 40)
    end
    return nil
end

local function get_cache_path(video_id)
    local home = os.getenv("HOME")
    return home .. "/.cache/chevren/" .. video_id .. ".srt"
end

local function on_file_loaded()
    local vid = get_video_id()
    if not vid then return end

    local path = mp.get_property("path")
    local cache_file = get_cache_path(vid)

    -- 1. Generate isteği gönder (Arka planda başlatır)
    local res = utils.subprocess({
        args = {
            "curl", "-s", "-X", "POST", "http://127.0.0.1:7373/generate",
            "-H", "Content-Type: application/json",
            "-d", '{"url":"' .. path .. '"}'
        }
    })

    -- Server kapalıysa veya hata varsa dur
    if not res or res.status ~= 0 then return end

    local start_ts = os.time()
    local timer
    
    -- 2. Polling (1.5 sn bir)
    timer = mp.add_periodic_timer(1.5, function()
        -- 600 saniye timeout
        if os.time() - start_ts > 600 then
            timer:kill()
            return
        end

        local status_res = utils.subprocess({
            args = {
                "curl", "-s", "http://127.0.0.1:7373/status?v=" .. vid
            }
        })

        if status_res and status_res.status == 0 then
            local status = utils.parse_json(status_res.stdout)
            if status and status.stage == "ready" then
                timer:kill()
                -- Altyazıyı ekle ve görünür yap
                mp.commandv("sub-add", cache_file, "select", "Chevren AI")
                mp.osd_message("Chevren: Altyazı hazır")
            end
        else
            -- Geçici curl hatalarında timer'ı öldürme, denemeye devam et
            -- timer:kill()
        end
    end)
end

mp.register_event("file-loaded", on_file_loaded)
