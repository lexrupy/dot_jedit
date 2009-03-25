#!/usr/local/bin/ruby
require 'yaml'
require 'erb'
require 'rexml/document'
require 'rdoc/ri/ri_descriptions'
require 'rdoc/markup/simple_markup/to_flow'

include RI

class JavaXmlSerializer

  def initialize(template_dir, result_dir)
    template_dir = template_dir + '/' if template_dir[template_dir.size-1] != '/'
    result_dir = result_dir + '/' if result_dir[result_dir.size-1] != '/'

    @template_dir = template_dir
    @result_dir = result_dir
  end
  
  def convert_dir(base_dir, dir)
    @base_dir = base_dir
    dir = dir.gsub(%[\\], %[/])
    Struct.new("File", :type, :path, :name, :dir)
    list = find_class_descriptions(dir)
    list.each do |file|
      convert(file)
    end
  end

  def find_class_descriptions(dir)
    list = Array.new

    Dir.foreach(@base_dir + dir) do |entry|
      if entry != "." and entry != ".."
        path = dir + "/" + entry
        if File.directory? @base_dir + path
          list << find_class_descriptions(path)
        elsif entry =~ /(cdesc-)(.*)(\.yaml)/
          list << Struct::File.new($2, @base_dir + path, entry, dir)
        end
      end
    end
    
    list.flatten!
    list
  end
  
  def convert(file)
    d = YAML.load_file(file.path)
    d.namespace = get_namespace(file.dir)
    d = add_method_descriptions(@base_dir + file.dir, d)
    puts file.name
    erb = ERB.new(IO.read(@template_dir + "cdesc.erb"))
    result = erb.result(binding)
    result_dir = create_dirs(file)
      
    File.open(%Q[#{result_dir}/#{file.type}.xml], "w") do |file|
      file.puts result
    end
  end

  def normalize(text)
    text.gsub!('&lt;', '|lt;')
    REXML::Text.normalize(text)
  end
  
  def get_method_description(description, dir, method, type)
    name = ''
    index = 0
    method.name.each_byte do |b|
      if b < 48 or (57 < b and b < 65) or (90 < b and b < 97 and b != 95) or 122 < b
        name << '%' + b.to_s(16)
      else
        name << method.name[index,1].to_s
      end
      index = index + 1
    end
    
    d = YAML.load_file(%Q[#{dir}/#{name}-#{type}.yaml])
    d.html_comment = convert_comment(d.comment)
  
    d.full_name = normalize(d.full_name)
    d.namespace = if description.namespace
                    description.namespace + "::" + description.name
                  else
                    description.name
                  end
    d.name = normalize(d.name)
    d.params = normalize(d.params) if d.params
    d.block_params = normalize(d.block_params) if d.block_params
    d.aliases.each do |a|
      a.name = normalize(a.name)
    end if d.aliases
  
    d
  end
  
  def convert_element(html,part)
      if part.instance_of? SM::Flow::P
        html << %Q[<p>#{part.body}</p>]
      elsif part.instance_of? SM::Flow::VERB
        html << %Q[<pre>#{part.body}</pre>]
      elsif part.instance_of? SM::Flow::H
        level = part.level
        text = part.text
        html << %Q[<h#{level}>#{text}</h#{level}>]
      elsif part.instance_of? SM::Flow::LI
        html << %Q[<li>#{part.body}<li>]
      elsif part.instance_of? SM::Flow::RULE
        html << '<hr />'
      else
        html << '<ul>'
        part.contents.each do |item|
          convert_element(html,item)
        end
        html << '</ul>'
      end
  end
  
  def convert_comment(comment)
    html = ""
    comment.each do |part|
      convert_element(html,part)
    end if comment
    normalize(html)
  end
  
  def add_method_descriptions(dir, description)
    description.i_methods = description.instance_methods.collect do |method|
                              get_method_description(description, dir, method, 'i')
                            end
    description.c_methods = description.class_methods.collect do |method|
                              get_method_description(description, dir, method, 'c')
                            end
    description.html_comment = convert_comment(description.comment)
  
    description.attributes.each do |a|
      a.html_comment = convert_comment(a.comment)
    end if description.attributes
    
    description.constants.each do |c|
      c.html_comment = convert_comment(c.comment)
      c.value = normalize(c.value).gsub('�','')
    end if description.constants
  
    description
  end
  
  def create_dir(dir)
    if !File.exist? dir
      Dir.mkdir(dir)
    end
  end
  
  def create_dirs(file)
    dir = @result_dir
    create_dir(dir)
    file.dir.each("/") do |part|
      dir = dir + "/" + part
      create_dir(dir)
    end
    dir
  end
  
  def get_namespace(dir)
    parts = dir.split('/')
    if parts.size > 3
      parts = parts[2..(parts.size-2)]
      return parts.join("::")
    else
      return nil
    end
  end

end

class NamedThing
  attr_accessor :html_comment
end

class Description
  attr_accessor :html_comment
  attr_accessor :namespace
end

class ModuleDescription
  attr_accessor :i_methods
  attr_accessor :c_methods
end

class Constant
  attr_writer :value
end

class AliasName
  attr_writer :name
end

