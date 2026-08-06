require 'net/http'
require 'uri'
require 'json'
require 'date'

# Default URL
default_url = "https://api.careerzenith.ai/job-board/user/?page=1"
site_url = ARGV[0] || default_url

# Parse URI
begin
  uri = URI.parse(site_url)
rescue => e
  puts "Error parsing URL: #{e.message}"
  exit 1
end

# Check and extract page parameter
params = URI.decode_www_form(uri.query || '').to_h
page = (params['page'] || 1).to_i

all_jobs = []

begin
  loop do
    # Re-build URI with current page number
    params['page'] = page.to_s
    uri.query = URI.encode_www_form(params)

    http = Net::HTTP.new(uri.host, uri.port)
    http.use_ssl = (uri.scheme == 'https')
    
    # Timeouts
    http.read_timeout = 10
    http.open_timeout = 10

    request = Net::HTTP::Get.new(uri.request_uri)
    response = http.request(request)

    if response.code != '200'
      break
    end

    data = JSON.parse(response.body)
    jobs = data['jobs'] || []
    all_jobs.concat(jobs)

    total_pages = (data['total_pages'] || 1).to_i
    break if page >= total_pages
    break if all_jobs.length >= 10 # if page 1 has 10 jobs, we don't need subsequent pages
    
    page += 1
  end
rescue => e
  if all_jobs.empty?
    puts "Error fetching jobs: #{e.message}"
    exit 1
  end
end

if all_jobs.empty?
  puts "No jobs found."
  exit 0
end

# Calculate relative posting date helper
def relative_date(created_at_str)
  return "N/A" if created_at_str.nil? || created_at_str.empty?
  begin
    created_date = Date.parse(created_at_str)
    today = Date.today
    diff = (today - created_date).to_i
    if diff <= 0
      "posted today"
    elsif diff == 1
      "posted 1 day ago"
    else
      "posted #{diff} days ago"
    end
  rescue => e
    "posted on #{created_at_str.split('T')[0]}"
  end
end

# Sort jobs by created_at descending (latest first)
sorted_jobs = all_jobs.sort_by { |job| job['created_at'] || '' }.reverse

# Select top 10 latest jobs
top_10 = sorted_jobs.first(10)

# Output Markdown Table
puts "| Company Name | Position | Apply Link | Posting Date |"
puts "| :--- | :--- | :--- | :--- |"

top_10.each do |job|
  company_name = job.dig('company', 'name') || "N/A"
  title = job['title'] || "N/A"
  apply_url = job['url'] || "#"
  posting_date = relative_date(job['created_at'])
  
  puts "| #{company_name} | #{title} | [Apply Link](#{apply_url}) | #{posting_date} |"
end
