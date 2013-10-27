<%inherit file="base.mako"/>
<%def name="title()">Search</%def>

<%def name="stylesheets()">
<link rel="stylesheet" type="text/css" href="/static/css/jquery.tagsinput.css" />
</%def>


<%def name="content()">
<section id="Search" xmlns="http://www.w3.org/1999/html">
    <div class="page-header">
        % if query:
##            split on and, so we will be able to remove tags
            <%
                components = query.split('AND')
            %>
        <h1>Search <small> for
##            for showing tags
            % for i, term in enumerate(components):
##              the first is not removable. we need it to query
                % if i != 0:
                    <a href='/search/?q=${query.replace('AND'+term, '') | h }' class="label label-success btn-mini"> ${term} <span class="badge">x</span></a>
                % else:
                    ${term}
                % endif
            % endfor
         <br>
##       number of results returned and the time it took
        ${total} result${'s' if total is not 1 else ''} in ${time} seconds</small></h1>
        % endif
##      if solr returned a spellcheck, display it
        % if spellcheck:
           <h4> Did you mean <a href='/search/?q=${spellcheck}'> ${spellcheck} </a>? </h4>
        % endif
    </div>
</section>
<div class="row">
    <div class="col-md-2">
        % if query:
        <h3>
##            our search users query
            <a href="/search/?q=user:${query|h}"> Search users </a>
        </h3>
        % endif
##        our tag cloud!
        % if tags:
        <h3> Improve Your Search:</h3>
            % for key, value in tags.iteritems():
                % if not (u' tags:"{s}"'.format(s=key) in components or u' tags:"{s}" '.format(s=key) in components):
                    <span id="whatever">
                    <a href="/search/?q=${query|h} AND tags:&quot;${key}&quot;" rel=${value}> ${key} </a>
                    </span>
                % endif
            % endfor
        % endif

    </div>
    <div class="col-md-10">
            % if results:
##            iterate through our nice lists of results
                % for result in results:
                    <div class="result">
##                    users are different results than anything associated with projects
                        % if 'user' in result:
                            <div class="user">
                            <a href=${result['user_url']}>${result['user']}</a>
                            </div>
                        % else:
                        <div class="title">
                            <h4>
                                % if result['url']:
                                    <a href=${result['url']}>${result['title']}</a>
                                %else:
                                    <span style='font-weight:normal; font-style:italic'>${result['title']}</span>
                                % endif

                            </h4>
                        </div>
##                            jeff's nice logic for displaying users
                        <div class="contributors">
                            % for index, (contributor, url) in enumerate(zip(result['contributors'][:3], result['contributors_url'][:3])):
                                <%
                                    if index == 2 and len(result['contributors']) > 3:
                                        # third item, > 3 total items
                                        sep = ' & <a href="{url}">{num} other{plural}</a>'.format(
                                            num=len(result['contributors']) - 3,
                                            plural='s' if len(result['contributors']) - 3 else '',
                                            url=result['url']
                                        )
                                    elif index == len(result['contributors']) - 1:
                                        # last item
                                        sep = ''
                                    elif index == len(result['contributors']) - 2:
                                        # second to last item
                                        sep = ' & '
                                    else:
                                        sep = ','
                                %>
                                <a href=${url}>${contributor}</a>${sep}
                            % endfor
                        </div>
##                      our highlight
                        <div class="highlight">
                            % if result['highlight'] is not None:
                                % for highlight in result['highlight']:
                                   %if hightlight:
                                       ${highlight}
                                   %endif
                                % endfor
##                      if there is a wiki link, display that
                                % if result['wiki_link']:
                                    <a href=${result['wiki_link']}> jump to wiki </a>
                                % endif
                            % endif
                        </div>
##                      if we have nested, we have to iterate by keys
##                      because many different nodes can be displayed in the nest
##                      section of the dictionary
                            % if result['nest']:
                                <div class="nested">
                                    % for i, key in enumerate(result['nest'].iterkeys()):
##                                      dont show more than 5 nodes
                                        % if i < 5:
                                            <div class="sub_title">
                                                <h4>
                                                    <a href=${result['nest'][key]['url']}>${result['nest'][key]['title']}</a>
                                                </h4>
                                            </div>
##                                           jeffs nice logic for displaying users, again
                                            <div class="contributors">
                                                % for index, (contributor, url) in enumerate(zip(result['nest'][key]['contributors'][:3], result['nest'][key]['contributors_url'][:3])):
                                                    <%
                                                        if index == 2 and len(result['nest'][key]['contributors']) > 3:
                                                            # third item, > 3 total items
                                                            sep = ' & <a href="{url}">{num} other{plural}</a>'.format(
                                                                num=len(result['nest'][key]['contributors']) - 3,
                                                                plural='s' if len(result['nest'][key]['contributors']) - 3 else '',
                                                                url=result['nest'][key]['url']
                                                            )
                                                        elif index == len(result['nest'][key]['contributors']) - 1:
                                                            # last item
                                                            sep = ''
                                                        elif index == len(result['nest'][key]['contributors']) - 2:
                                                            # second to last item
                                                            sep = ' & '
                                                        else:
                                                            sep = ','
                                                    %>
                                                    <a href=${url}>${contributor}</a>${sep}
                                                % endfor
                                            </div>
                                            % if result['nest'][key]['highlight'] is not None:
                                            <div class="highlight">
##                                               show our highlights
                                                % for highlight in result['nest'][key]['highlight']:
                                                    ${highlight}
                                                % endfor
##                                               and link to wiki, if its there
                                                % if result['nest'][key]['wiki_link']:
                                                       <a href=${result['nest'][key]['wiki_link']}> jump to wiki </a>
                                                % endif
                                            </div>
                                             % endif
                                    % else:
##                                           if we've shown more than 5 nested nodes, link to project and break
                                            <h4> <a href=${result['url']}> and ${len(result['nest'].keys()) - i} more... </a>  </h4>
                                            <%
                                                break
                                            %>
                                    % endif
                                    % endfor
                                </div>
                                % endif
##                      show all the tags for the project
                        <div class="tags">
                            % if 'tags' in result:
                                % for tag in result['tags']:
                                <a href=/search/?q=${tag} class="label label-info btn-mini"> ${tag} </a>
                                % endfor
                            % endif
                        </div>
                        </div>
                        <br>
                    %endif
                % endfor
##            pagination! we're simply going to build a query by telling solr which 'row' we want to start on
                <div class="navigate">
                    % if total > 10:
                        % if current_page >= 10:
                            <a href="?q=${query | h}&pagination=${(current_page)-10}">Previous</a>
                        % endif
                            % for i, page in enumerate(range(0, total, 10)):
                                % if i == current_page/10:
                                   ${i+1}
                                % else:
                                    <a href="?q=${query | h}&pagination=${page}">${i+1}</a>
                                % endif
                            % endfor
                        % if current_page < (total-10):
                            <a href="?q=${query | h}&pagination=${(current_page)+10}">Next</a>
                        % endif
                    % endif

                </div>
            % else:
                No results found. <br />
            %endif
    </div>
</div>
</%def>
