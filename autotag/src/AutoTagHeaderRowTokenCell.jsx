import React from 'react';
import ReactTooltip from 'react-tooltip';

import AutoTagHeaderRowMapMenuItem from './AutoTagHeaderRowMapMenuItem';

export default class AutoTagHeaderRowTokenCell extends React.Component {

  constructor() {
    super();

    // Prebind this to callback methods
    this.handleCheckedChangeAll = this.handleCheckedChangeAll.bind(this);
  }

  isChecked() {

    for (let image of this.props.images) {
      if (!image.checkedTokens.has(this.props.token)) {
        return false;
      }
    }
    return true;

  }

  isDisabled() {
    return this.props.tag === null;
  }

  handleCheckedChangeAll() {
    this.props.handleCheckedChangeAll(this.props.token, !this.isChecked());
  }

  render() {
    let token = this.props.token;
    let tag = this.props.tag;

    // If there are options for mapping this tag, create menu items for them
    let menuNodes = [];

    menuNodes = [...token.possible].map(tag =>
      <AutoTagHeaderRowMapMenuItem key={tag.id}
                                   token={token}
                                   tag={tag}
                                   textValue={tag.value}
                                   selectMapping={this.props.selectMapping} />
    );

    // Set default (i.e. unmatched) tagValue to non-breaking space
    let tagValue = '\u00a0';
    let dropDownClassname = "tag_inner";
    if (tag !== null) {
      tagValue = tag.value;
    } else {
      dropDownClassname += " tagInactive";
    }

    let className = '' + token.type + 'Tokens';
    let tooltipID = 'tooltip-token-' + token.value;

    return (
      <th className={className}>
        <div className={'token'}>{token.value}
          <input type="checkbox"
                 checked={this.isChecked()}
                 disabled={this.isDisabled()}
                 onChange={this.handleCheckedChangeAll} />
        </div>
        <div className={'tag'}>
          <span style={{position: 'relative'}}>

            <a className={dropDownClassname}
               data-tip
               data-for={tooltipID}>{tagValue}
            </a>
            {
              tag &&
              <ReactTooltip id={tooltipID} place="bottom" type="dark" effect="solid">
                <ul>
                  <li><strong>ID:</strong> {tag.id}</li>
                  <li><strong>Value:</strong> {tagValue}</li>
                  {
                    tag.description &&
                    <li><strong>Description:</strong> {tag.description}</li>
                  }
                  <li><strong>Owner:</strong> {tag.owner.omeName}</li>
                </ul>
              </ReactTooltip>
            }

            <span className={'showTag dropdown-toggle'}
                  data-toggle="dropdown"
                  style={{display: 'none'}}>X</span>

            <ul className={'dropdown-menu'} role="menu">
              {menuNodes}
              <AutoTagHeaderRowMapMenuItem tag={null}
                                           token={token}
                                           textValue="(Select None)"
                                           selectMapping={this.props.selectMapping} />
              <li className={'divider'}></li>
              <li><a className={'token-map'} onClick={this.props.newMapping.bind(null, token)}>New/Existing Tag</a></li>
            </ul>

          </span>
        </div>
      </th>
    );
  }
}
